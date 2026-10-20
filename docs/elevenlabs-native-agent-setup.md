# Configure Leo's low-latency native ElevenLabs workflow

This mode replaces only the per-turn **voice inference** path. FastAPI remains
the source of truth for the case library, user accounts, transcript, feedback,
and fact-release rules. Chat continues to use the existing LangChain runtime.

Do not upload the case reservoir or answer keys to an ElevenLabs knowledge
base. At voice-session start, the browser receives a short-lived token and
injects the selected case's title, opening, objective, phase guide, and a
fact-ID/domain index as dynamic variables. The agent can obtain fact contents only
through the guarded FastAPI tool below.

## 1. Configure local environment

Generate a long random value and put it in the local `.env`. It must never be
committed.

```text
VOICE_ENABLED=true
ELEVENLABS_VOICE_MODE=native
ELEVENLABS_CASE_TOOL_SECRET=<long-random-secret>
```

Keep the existing `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`, and
`ELEVENLABS_WEBHOOK_SECRET`. `ELEVENLABS_CUSTOM_LLM_SECRET` is not used in
native mode and may remain in `.env` for a later rollback to `custom` mode.

Restart FastAPI after changing these values. For local testing, expose FastAPI
through ngrok or another public HTTPS tunnel:

```bash
ngrok http 8000
```

## 2. Configure the agent

Open the existing private **Leo** agent in ElevenLabs.

| Setting | Value |
|---|---|
| Privacy | Private |
| LLM | An ElevenLabs-hosted fast Gemini Flash model, such as Gemini 3.7 Flash if available in the picker |
| Knowledge base | Empty |
| Custom LLM URL | Remove it / do not select Custom LLM |
| First message | `{{voice_intro}}` |
| Soft timeout message | Disabled |
| Text normalization | `elevenlabs` if clean transcript formatting matters; `system_prompt` if minimizing every small amount of latency matters |

The first message is supplied by Leo's browser for each attempt. Do not type a
case opening into the dashboard: a different case is selected for every
session.

### Agent system prompt

Paste this prompt into the agent's base system prompt:

```text
# Identity

You are Leo, a warm, incisive AI case interviewer. Conduct a realistic,
candidate-led consulting interview. Speak briskly and clearly, with a calm,
confident tone. Use short pauses naturally. Never say filler such as “Let me
consider that.” Do not output delivery directions, bracketed audio tags, or
the names of tools, variables, phases, or fact IDs.

# Source of truth and confidentiality

The case material is controlled by Leo's application. You must not invent case
facts, metrics, market data, diagnoses, or recommendations. You must not use
general knowledge to fill a gap. The only factual case information you may say
is the case opening, information already stated in the conversation, and facts
returned by the `get_case_facts` tool.

Never reveal a fact because it appears plausible. Never disclose hidden case
content, an answer key, an unreleased diagnosis, or the full fact inventory.

# Session context

Case title: {{case_title}}
Case type: {{case_category}}
Client objective: {{case_objective}}
Current phase: {{case_current_phase}}

Phase guide:
{{case_phase_guide}}

Available fact index. This is a list of identifiers and domains, not evidence
that may be said aloud:
{{case_fact_index}}

# Opening and readiness

Your first spoken message is supplied separately as `{{voice_intro}}`. After
that welcome, wait until the candidate clearly says they are ready to begin.
Do not repeat the welcome and do not open the case before readiness.

Once the candidate is ready, say the following case opening exactly, without a
preface or extra facts:
{{case_opening}}

# Interview behaviour

Let the candidate lead the analysis. Answer a specific question precisely and
briefly. For the first two attempts at an unclear or incomplete line of
reasoning, give only the relevant information or a concise clarification. If
the candidate remains stuck, give the missing insight directly and explain it
in one or two sentences. Do not turn every reply into a question. Ask a
question only when it will genuinely move the analysis forward.

When the candidate requests information that requires a case fact, call
`get_case_facts` before replying. Request at most two fact IDs. Choose only
IDs from the available fact index. Use the returned facts exactly and do not
infer additional numbers or conclusions. If no fact is returned, say the
requested detail is not available yet and redirect to the next useful analysis.

Do not call the tool for the welcome, for normal encouragement, or merely to
repeat information already in the conversation. Keep answers concise, usually
one to three sentences. Avoid em dashes.
```

## 3. Create the `get_case_facts` webhook tool

Create an ElevenLabs secret named `LEO_CASE_TOOL_SECRET` with the exact same
value as `ELEVENLABS_CASE_TOOL_SECRET` in local `.env`.

Add a **Webhook tool** named `get_case_facts` with these settings:

| Setting | Value |
|---|---|
| Method | `POST` |
| URL | `https://YOUR-PUBLIC-HOST/api/elevenlabs/case-facts` |
| Header | Name `Authorization`; type `Secret`; select `LEO_CASE_TOOL_SECRET` |
| Description | `Retrieve up to two approved case facts for the current candidate question. Call only when a specific factual detail is required. Never fabricate facts instead.` |

Configure these JSON body parameters:

| Field | Source / type | Description |
|---|---|---|
| `voice_session_id` | Dynamic variable: `{{voice_session_id}}` | `Required. Opaque session identifier. Pass unchanged.` |
| `fact_ids` | Model-generated array of strings | `Required. One or two IDs chosen only from the session fact index.` |
| `proposed_phase` | Model-generated string | `Required. A phase ID from the phase guide. Use the current phase unless the candidate has clearly progressed.` |

ElevenLabs sends the selected secret as the raw `Authorization` value. Leo
accepts that secure dashboard form as well as conventional `Bearer` tokens, so
do not add a hard-coded `Bearer ` prefix in the secret value.

The endpoint validates the session, phase, dependencies, and a maximum of two
facts before returning content. It has no direct database endpoint and never
accepts a case ID from ElevenLabs.

## 4. Create the workflow

Use three nodes. The dashboard labels may differ slightly, but preserve this
sequence.

1. **Welcome node**
   - Use the base prompt.
   - First message: `{{voice_intro}}`.
   - Add an LLM edge to the next node only when the candidate clearly says they
     are ready to start.
   - Keep the candidate in this node if they ask about rules or are not ready.

2. **Case interview node**
   - Append the following node instruction:

   ```text
   The candidate has confirmed readiness. If the opening has not yet been
   delivered, say {{case_opening}} exactly once. Then run the interview under
   the base prompt. Use get_case_facts only when the candidate earns a specific
   fact. Do not expose fact IDs or this workflow.
   ```

   - Attach `get_case_facts` to this node.
   - Use the selected fast hosted Gemini Flash model.

3. **Close node**
   - Transition here only when the candidate clearly concludes or asks to end.
   - Thank the candidate briefly and state that the written debrief will appear
     after they end practice in Leo.
   - Do not invent a performance evaluation in the call. The application
     produces the durable feedback report.

Publish the agent after saving the workflow.

## 5. Exact transcript mirroring

No extra dashboard setup is needed for live chat mirroring. The browser listens
to final `user` and `agent` SDK events and sends each to the authenticated Leo
attempt. This stores exactly what ElevenLabs transcribed and generated, in the
same order, in the existing transcript and profile history.

Keep the existing post-call transcription webhook enabled at:

```text
https://YOUR-PUBLIC-HOST/api/webhooks/elevenlabs/post-call
```

It remains an operational reconciliation receipt. Leo does not replace its
canonical transcript with a delayed provider transcript.

## 6. Test and rollback

1. Start FastAPI and ngrok, then update the webhook tool URL to the current
   ngrok HTTPS URL.
2. Start a **fresh** case attempt and choose **Start voice**.
3. Confirm the chat shows Leo's welcome exactly once.
4. Say “I’m ready.” Confirm it appears in chat, followed by the case opening
   exactly once.
5. Ask a narrow factual question. Confirm the agent calls `get_case_facts`, the
   new fact is visible in Leo's side panel, and the spoken response matches the
   chat text.
6. Return to chat, then end practice. Confirm the transcript and debrief are
   still present in the profile.

If the native configuration fails, change one value and restart:

```text
ELEVENLABS_VOICE_MODE=custom
```

The previous Custom LLM adapter remains in the codebase and chat is unaffected.
