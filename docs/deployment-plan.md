# Deployment plan

Target: 10 to 20 users now, headroom to roughly 1,000 within a couple of months,
without a rewrite in between.

## 1. Critique of the plan that exists

There is no deployment plan. There are three fragments, and one of them is
actively misleading.

**`docs/engineering-design.md` §10 is for an architecture that no longer exists.**
It describes Cloudflare Workers, Durable Objects, `.openai/hosting.json`,
`worker/index.ts` and `vite.config.ts`, and says promoting the attempt store into
a Durable Object is "mechanical rather than a rewrite". None of those files are in
the repository. This is a FastAPI application with SQLite and Jinja templates.
Anyone following that section would be building the wrong thing. It should be
marked superseded rather than quietly left in place.

**`docs/implementation-roadmap.md` phase 7** is one table row: "Remove legacy
paths, consolidate docs, add authentication, shared persistence, observability,
and rate limits." Authentication is done. The rest is a list of nouns, not a plan.

**`README.md` "Deployment boundary" is the only accurate part.** It correctly
names three things: SQLite suits one instance, `SESSION_SECRET` must be set
explicitly or instances reject each other's cookies, and secrets belong in the
host's secret manager. Keep all three.

What none of them mention, and what actually decides whether this deploys
successfully:

- **HTTPS is a functional requirement, not a nicety.** `getUserMedia` and
  `AudioWorklet.addModule` both require a secure context. Over plain HTTP the
  entire voice feature fails, and it fails at the microphone rather than with a
  useful error.
- **The OAuth redirect URI is pinned to `127.0.0.1:8000`** and must be re-registered
  in Google Cloud Console against the production origin before anyone can sign in.
- **`data/` is gitignored and holds everything**: accounts, attempts, transcripts,
  evaluations, and the generated session secret. On a platform without a mounted
  volume, every deploy destroys all of it.
- **This is a metered product.** Each turn spends an LLM call, a speech-to-text
  upload and a speech-synthesis stream. Nothing in the repository caps that per
  user, and `ALLOWED_EMAIL_DOMAINS` is optional, so an unset value means anyone
  with a Google account can sign up and spend the budget.
- **Streaming.** `/api/attempts/{id}/turn/stream` is server-sent events. A
  buffering proxy in front of it silently destroys the sentence-level speech
  pipeline, which is most of the latency work.
- **Python.** Development runs 3.14; `pyproject.toml` only says `>=3.11`. An image
  has to pin something specific.

## 2. Measured constraints

Numbers from this machine, so the plan argues from evidence rather than instinct.

**Python version.** The dependency set resolves unchanged on 3.12 and 3.13, and
the suite is identical on 3.13 (236 passed, same single pre-existing failure).
3.13 also drops the `pydantic.v1 is not compatible with Python 3.14` warning that
3.14 emits. **Pin 3.13.**

**SQLite concurrency.** Eight to a hundred concurrent writers, 10 writes each, at
a ~13KB payload matching a real attempt save:

| concurrent writers | current (default journal) | with WAL | speedup |
|---|---|---|---|
| 8 | 82ms | 44ms | 1.9× |
| 25 | 1,221ms | 267ms | 4.6× |
| 50 | 2,032ms | 888ms | 2.3× |
| 100 | 1,726ms | 1,615ms | 1.1× |

Two conclusions, one of which corrects an assumption I started with. **SQLite does
not fail under this load, it slows** — zero `database is locked` errors at any
level, because the 5s busy timeout absorbs the contention. So the common claim
that SQLite breaks past a handful of users is not true here, and there is no need
for Postgres on day one. But **WAL is worth 4.6× at 25 concurrent writers**, which
is the band a few hundred users actually peak in, and it costs one line.

**Request concurrency.** 57 of 58 route handlers are synchronous, so they execute
on Starlette's thread pool, default 40 threads. A chat turn occupies one thread
for the 3–5 sequential model calls; a voice turn's SSE generator occupies one for
the whole stream. Forty simultaneous turns saturates it and the rest queue. At 20
users this is irrelevant. At 1,000 it is the first thing to raise.

**Image weight.** Application plus content is ~5.7MB (`app` 1.3MB, `corpus` 3.2MB,
`knowledge_base` 868KB, `reservoir` 312KB, `evaluation` 28KB). `.venv` is 94MB and
`.git` 10MB and neither belongs in the image. A slim Python base plus dependencies
lands around 250–400MB. No system packages are needed: all audio work happens in
the browser, so there is no ffmpeg or codec dependency.

## 3. Platform: Fly.io

Chosen for four properties this application actually needs.

**A persistent volume, so SQLite works today with no database migration.** Given
the measurements above, SQLite is genuinely adequate for this scale, and avoiding
Postgres on day one removes the largest piece of work from the critical path.

**No cold starts.** A machine kept warm answers immediately. On a scale-to-zero
platform the first turn after idle pays container start plus interpreter start
plus a 69-case catalogue load, which lands directly on the latency this product
was just rebuilt to protect.

**Docker-native**, which is wanted anyway, and streams SSE and WebSockets without
buffering.

**Region pinning.** `bom` (Mumbai) puts the server next to the users. Note what
this does and does not affect: speech-to-text upload and speech synthesis go
browser-to-ElevenLabs directly, so they are unaffected by server location. What
moves is the two browser-to-server round trips per turn, and the server-to-
OpenRouter hop, which moves the other way. Measure before assuming; the model call
dominates either way.

Cost at this scale: one `shared-cpu-1x` machine with 512MB–1GB and a 1–3GB volume
is roughly $5–15/month.

**Rejected, with reasons.** *Cloud Run*: the natural choice at 1,000 users, but its
ephemeral filesystem rules out SQLite entirely, so it forces the Postgres
migration on day one, and its cold starts hurt exactly the path that matters. It
is the right destination later, not now. *Render*: a close second and simpler; the
same persistent-disk single-instance constraint, marginally pricier at scale, pick
it if Fly's CLI is unwelcome. *A bare VPS*: cheapest and worst use of time — TLS
renewal, OS patching, backups and deploy scripting for twenty users. *Vercel or
Netlify*: not suitable, this is a stateful long-request Python server.

## 4. Phase 0 — before any deploy

Six changes in the repository. None are large; all of them break something in
production if skipped.

1. **WAL on every SQLite connection.** Four call sites: `app/store.py:461`,
   `app/store.py:605`, `app/accounts.py:248`, and the inline connections in
   `app/admin.py`. Set `journal_mode=WAL`, `synchronous=NORMAL`,
   `busy_timeout=5000`. Worth 4.6× per the table above. Best done as one shared
   helper so a fifth call site cannot forget.
2. **`Cache-Control` on static assets.** Currently absent, so every asset
   revalidates on every page load. Hash the filenames or set a long max-age with
   an explicit revalidation path.
3. **Set `SESSION_SECRET` explicitly.** Without it the value is generated into the
   volume; with a volume that survives, but it must not depend on that.
4. **Production `OAUTH_REDIRECT_URI`** plus the matching authorised redirect URI
   registered in Google Cloud Console.
5. **Set `ALLOWED_EMAIL_DOMAINS`.** Unset means any Google account can register and
   spend the API budget. For a pilot of 10–20 this is the cheapest possible abuse
   control.
6. **Retire the stale design section.** Mark `docs/engineering-design.md` §10
   superseded and point it here.

## 5. Phase 1 — Docker

A two-stage build, pinned to `python:3.13-slim`.

- **Stage one** installs dependencies with `uv sync --frozen --no-dev` against the
  committed `uv.lock`, so the image is reproducible and the resolver never runs at
  build time.
- **Stage two** copies the virtual environment and only what runs: `app/`,
  `reservoir/`, `corpus/`, `knowledge_base/`, `evaluation/`. A `.dockerignore`
  excludes `.venv`, `.git`, `data/`, `tests/`, `docs/`, `__pycache__` and `.env` —
  that last one is the important line, since baking a secrets file into an image
  layer is the classic way to leak keys.
- **Run as a non-root user**, with `/data` owned by it and declared as the volume
  mount point.
- **One uvicorn worker.** This is not a performance oversight: SQLite has a single
  writer, and multiple workers on one volume would contend for it. Raise
  concurrency by lifting the thread pool, not by adding workers, until the move to
  Postgres.
- **`HEALTHCHECK` against `/health`**, which already exists and reports whether the
  interviewer and evaluator constructed.

Verification, in order: the image builds; the suite passes inside it; the
container serves `/health` locally with a bind-mounted `data/`; the room loads and
a typed turn completes. Only then push.

## 6. Phase 2 — first deploy

1. `fly launch --no-deploy`, one machine, region `bom`.
2. Create and mount a volume at `/data`; point `DATABASE_PATH` at it.
3. `fly secrets set` for every value currently in `.env`. Secrets are
   environment-injected and never written to an image layer.
4. Register the Fly hostname as an authorised redirect URI in Google Cloud
   Console, then deploy.
5. Smoke test in this order, because each step gates the next: `/health` → Google
   sign-in → a typed turn → **a spoken turn end to end** → end the case and open
   the debrief.

The spoken turn is the one that cannot be inferred from a green test suite. It is
also the step that will expose an HTTPS or a proxy-buffering problem immediately,
which is why it comes before anyone is invited in.

## 7. Phase 3 — cost and abuse control

This matters more than performance at this scale. Every turn spends real money on
three vendors.

**On the same keys in production.** You asked to reuse the development keys and
that is workable, but be clear about what it costs: development and production
spend become indistinguishable, and a leak forces a rotation that takes both down
at once. Two mitigations that do not require separate keys — set an explicit
credit limit on the OpenRouter key so a loop cannot drain the account, and keep
the ElevenLabs key scoped to only `text_to_speech`, `speech_to_text` and
single-use tokens, which it already is after this week's fix. Separate keys per
environment is the thing to do at the point real users depend on uptime, not now.

**In the application:** a per-user daily turn cap, and a per-attempt turn cap.
Both are cheap to add next to the existing case-progress guard, and both bound the
worst case to something you can name in advance.

**On the vendors:** spend alerts on OpenRouter and ElevenLabs, and check the
ElevenLabs plan's concurrent-request limit before inviting more than a handful of
people, since each live candidate holds one synthesis socket.

## 8. Phase 4 — observability

Enough to answer "why was that turn slow" without a debugger.

- Structured logs for one line per turn: transport, model, recorded seconds,
  transcription latency, time to first sentence, facts released. Most of these are
  already logged individually; make them one parseable record.
- Alert on the failure modes this build has actually produced: a spoken turn
  falling back to the chat pipeline, an under-delivered approved fact from the
  post-hoc audit, and synthesis producing no audio.
- **Back up the volume.** A nightly copy of the SQLite file off-machine, with one
  documented restore that has actually been run once. An untested backup is not a
  backup, and this file holds every transcript and debrief.

## 9. Scaling triggers

Do none of this speculatively. Each has a signal.

| Signal | Action |
|---|---|
| Sustained >30 concurrent turns, requests queueing | Raise the Starlette thread pool above 40 |
| Sustained >25 concurrent writers, or a second instance is needed | Move to Fly Postgres. This is the only change that is not incremental, so it is the one to see coming |
| Voice latency dominated by the model call | Revisit `VOICE_OPENROUTER_MODEL` with `scripts/bench_turn.py`, which already measures exactly this |
| ElevenLabs concurrency limit reached | Upgrade the plan; each live candidate holds one socket |
| Read-heavy pages slow under load | Cache the case catalogue in memory; it is immutable per deploy |

The honest sequence is: SQLite plus one warm machine carries this comfortably to a
few hundred users. The wall is not user count, it is the first moment you need two
instances, because that is what SQLite cannot do. Everything before that is
configuration.

## 10. What this plan deliberately excludes

Kubernetes, a queue, Redis, autoscaling groups, a CDN, and multi-region. At 20
users each of these adds a failure mode and removes nothing. The migration path
above reaches 1,000 users without any of them.

## 11. Known-unverified

Stated plainly so it is not discovered later.

- **No spoken turn has ever run against real microphone audio.** Every voice fix
  this week was verified at the server, transport and invariant layers, and by a
  synthetic-MediaStream harness. The browser pane blocks microphone access, so PCM
  decode, gapless playback and barge-in have not been exercised by a real voice.
  The first production smoke test is the first real test.
- **`tests/test_case_progress.py` fails** on a `syncTimer` call removed by the
  in-progress timer work in `app/static/app.js`. Resolve before deploying, either
  by finishing that refactor or updating the test.
