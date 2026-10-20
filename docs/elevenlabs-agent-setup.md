# Configure Leo's ElevenLabs Agent

The application now has a feature-gated WebRTC voice path. Chat remains the
default and works independently of every setting below.

## 1. Finish the server configuration

Add a new random value to the local `.env`; it is separate from the ElevenLabs
API key:

```text
ELEVENLABS_CUSTOM_LLM_SECRET=<long-random-secret>
VOICE_ENABLED=false
```

Keep voice disabled while configuring the agent. Do not commit `.env`.

## 2. Configure the agent in ElevenLabs

Open the private Leo agent and use these settings:

| Setting | Value |
|---|---|
| Privacy | Private |
| First message | `{{voice_intro}}` |
| Knowledge base | Empty |
| Agent tools | None for V1 |
| LLM | Custom LLM |
| Model ID | `leo` |
| Server URL | `https://YOUR_PUBLIC_HOST/v1/chat/completions` |
| API key secret | Create an ElevenLabs secret whose value exactly matches `ELEVENLABS_CUSTOM_LLM_SECRET` |
| Custom LLM extra body | Enable this agent override / client event setting |

Replace the agent system prompt with the following. It is a delivery boundary,
not the source of case facts. Leo's application endpoint is the only component
allowed to decide facts, phases, or scores.

```text
You are Leo, a warm, incisive AI case interviewer. Your role is to deliver the
server-generated interview dialogue clearly and naturally. Do not invent case
facts, reveal a diagnosis, answer a case question from your own knowledge, or
override the server's sequencing.

Delivery: speak at a brisk, clear conversational pace with short pauses. Be
warm and confident in the welcome, calm and precise during analysis, and
respectful when correcting the candidate. Never use filler such as “Let me
consider that.”

Do not output audio tags, bracketed directions, or words that describe delivery.
The Custom LLM path treats them as literal speech. Use natural tone only. Speak
the exact server-generated text without adding, removing, paraphrasing, or
answering from your own knowledge.

Runtime binding: VOICE_SESSION_ID={{voice_session_id}}
```

Set the agent's first message to this exact dynamic variable:

```text
{{voice_intro}}
```

Leo's browser supplies both values at voice-session start. The first one lets
the Custom LLM adapter locate the authenticated attempt. The second is Leo's
warm pre-case briefing: it explains the interview hygiene and asks for the
candidate's readiness without revealing the detailed case. The Custom LLM then
uses an LLM-led readiness check and starts the actual case only after the
candidate has opted in. No case facts or answer key are configured in
ElevenLabs.

Leo also supplies a signed `customLlmExtraBody` when it starts a browser
connection. ElevenLabs forwards this as `elevenlabs_extra_body` on every
Custom LLM request, which keeps the local voice-session binding independent of
prompt history. In the Agent dashboard, enable **Custom LLM extra body** in
the agent's Security or Overrides section. Without it, a later provider turn
can lose its attempt binding and never reach Leo's runtime.

For Custom LLM calls, Leo first answers promptly from the provider callback,
then reconciles the visible candidate bubble with the browser SDK's final ASR
event. This replaces a provisional transcript such as “I'm ready” with the
exact final provider transcript, such as “I'm ready. Let's get started.” It
does not rewrite Leo's response or change released evidence.

For a quicker, more natural first response, disable the agent's **Soft timeout
message** while testing. A soft-timeout filler such as “Let me consider that”
is spoken by ElevenLabs before Leo's server-generated answer is available; it
does not mean that the case runtime received a turn. This Agent view does not
offer a speed slider, so the brisk-pace instruction above and concise server
turns are the appropriate controls. Use a warm, moderately expressive delivery
and do not set an aggressive interruption setting: Leo should wait for the
final candidate utterance before invoking the case runtime.

## 2.1 Conversation reliability settings

Open **Agent settings → Conversation flow / Advanced** and use these settings
for a 30-minute case interview:

| Setting | Recommended value | Why |
|---|---|---|
| Maximum conversation duration | `2100` seconds | The platform default can be 10 minutes; this covers a 30-minute case plus setup. |
| Turn eagerness | `Patient` | Candidates pause while structuring and calculating. |
| Take turn after silence | `12–15` seconds | Avoids treating a thinking pause as the end of an answer. |
| Speculative turn | Disabled | Leo's Custom LLM callback mutates the authoritative attempt only after a final candidate turn. A speculative, pre-final callback can otherwise make a partial utterance look final. |
| Soft timeout | Disabled | Prevents provider filler from becoming a fake Leo turn. |
| Interruptions | Disabled for the beta | Stops room noise, keyboard noise, and speaker bleed from cutting Leo off mid-answer. |

ElevenLabs' agent VAD already filters background noise, but the browser SDK
used by Leo does not expose a microphone `noiseSuppression` control for its
own WebRTC capture. The current permission preflight is therefore not active
noise cancellation. For materially noisy rooms, use headphones and select the
operating system's voice-isolation feature or a virtual microphone noise-
cancellation device. Once calls are stable, interruptions can be re-enabled
and tested with a high threshold and ignore terms for small backchannels such
as “mm-hmm”.

## 2.2 Reduce voice latency

Leo now supports a voice-only OpenRouter model override. Add a fast model ID
that is available in your OpenRouter account to `.env`, then restart FastAPI:

```text
VOICE_OPENROUTER_MODEL=<your-fast-OpenRouter-model-id>
```

Voice turns use this model for both the private director and the final Leo
reply, with smaller token budgets and at most one retry. Typed chat continues
using `OPENROUTER_MODEL`. The remaining latency comes from end-of-speech
detection, the HTTPS tunnel, two sequential model calls required for safe fact
validation, and TTS. For local testing, keep ngrok running in the nearest
region and disable any agent soft-timeout filler. A deployed backend will avoid
the tunnel hop.

The server URL must be public HTTPS. For a local integration check, expose the
running FastAPI service through a temporary HTTPS tunnel. Do not use the agent
preview for a real case before the Custom LLM setting is published: its native
LLM does not use Leo's runtime.

## 3. Enable a narrow test

Once the Custom LLM endpoint is public and the agent has been republished:

1. Set `VOICE_ENABLED=true` locally and restart FastAPI.
2. Sign in to `/practice` and start a fresh case.
3. The **Start voice** control appears only when all required voice variables
   are present. Accept the microphone notice.
4. Hear Leo's introduction, say that you are ready, and confirm the detailed
   case opening is spoken only then. The “ready” utterance must appear in the
   text transcript.
5. Ask one narrow case question and confirm the text transcript receives
   exactly one candidate turn and one Leo reply.
6. Select **Return to chat** and confirm the normal composer is immediately
   usable.

If a voice session cannot start or disconnects, the candidate remains in the
same attempt and can continue in chat.

## 4. Add the post-call webhook after public deployment

Create a workspace webhook with this URL:

```text
https://YOUR_PUBLIC_HOST/api/webhooks/elevenlabs/post-call
```

Enable HMAC signing, copy the generated shared secret into
`ELEVENLABS_WEBHOOK_SECRET`, and attach it to the Leo agent's post-call
transcription event. Leo verifies the signature and records only a reconciliation
receipt. It does not store provider audio or a duplicate provider transcript.

## What the implementation enforces

- A server-issued WebRTC token binds one provider session to one authenticated
  Leo attempt.
- The browser never sees `ELEVENLABS_API_KEY` or the Custom LLM secret.
- ElevenLabs Custom LLM requests are authenticated and use the same idempotent
  turn service as `POST /api/attempts/{id}/turn`.
- Chat needs neither ElevenLabs nor the voice feature flag.
