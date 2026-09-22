# Oxford MSWIN Scanner

A single-file web scanner for the **Oxford / Lafayette County, Mississippi MSWIN** P25 trunked radio
system, built on the public [OpenMHz](https://openmhz.com/system/oxfmswin) feed.

Live page: _(enable GitHub Pages to populate)_

## What it does

- **Live call log** — polls for new calls every 5s, newest first, with agency color stripes
  (blue = law enforcement, orange = fire, green = EMS, gold = campus, violet = emergency management).
- **Scan mode** — autoplays new calls oldest-first as they arrive and auto-advances, like a real scanner.
- **Per-talkgroup alerts** — a two-tone chirp plus a desktop notification when a chosen talkgroup keys up.
- **Talkgroup filter** across all 35 groups, grouped by agency. Selections, alerts, and volume persist
  in `localStorage`.
- **Activity strip** — calls per minute over the last 30 minutes.
- **Archive** — jump to any date and time within the retention window and see a window of traffic
  around that moment (50 calls before it, 50 after), then page further in either direction with
  Load earlier traffic / Load later traffic. Historical calls never fire alerts or enter the scan
  queue.
- **Search by what was said** — transcribes past traffic with a Whisper model running locally in
  the browser, then searches those transcripts. Forgiving by design: it expands a query through a
  dispatch vocabulary (a search for *wreck* also finds "10-50", "MVA", "rollover") and tolerates a
  slip or two per word, because Whisper mangles radio audio. Needs a one-time proxy setup — see
  below. Transcripts are stored locally and appear inline under each call in the log.

No build step and no dependencies. Open `index.html` directly or serve it anywhere static.
The one exception is transcript search, which needs a small proxy of your own — the next section
explains why.

## Searching what was said

Press <kbd>/</kbd>, or **Search traffic** in the header.

Transcription runs **in your browser**, on your own GPU, using Whisper via
[transformers.js](https://huggingface.co/docs/transformers.js) and WebGPU. There is no API key,
no per-call cost, and no audio sent to a transcription service. The model weights (45–260 MB
depending on the setting) come from a CDN once and are then cached by the browser; transcripts go
into IndexedDB and persist across reloads.

Pick a range, press **Transcribe this range**, and the page walks that window of history,
transcribing each call. Then search it. **Transcribe live traffic** keeps the index growing on its
own as new calls arrive.

Query syntax, beyond plain words:

| You type | It means |
|---|---|
| `wreck` | that word, its variants, and the dispatch phrasings for it |
| `"fire line"` | that exact phrase, required |
| `shots -alarm` | matches *shots*, excludes anything saying *alarm* |
| `tg:53682` or `tg:opd` | only that talkgroup |

**Smart match** does the expansion and fuzzy matching. **Exact words** does neither. **Regex** hands
your pattern straight to the regex engine.

### Why it needs a proxy

`media*.openmhz.com` will happily play audio to an `<audio>` element but sends no
`Access-Control-Allow-Origin` header, so the page is not allowed to *read* the bytes — and Web
Audio treats the element as tainted and hands back silence. Playback works; transcription cannot.

`proxy/worker.js` is a Cloudflare Worker that fetches the same public file server-side and
re-serves it with that one header. It stores nothing and only talks to openmhz.com. Deploy it
(`cd proxy && npx wrangler deploy`), paste the URL into **Settings**, press **Test**. Full
instructions in [proxy/README.md](proxy/README.md).

### How much to trust a transcript

Not very much, word for word. These are short bursts of compressed, noisy, clipped trunked audio
full of proper nouns, street names, unit numbers and plate readbacks — the worst case for any
speech model. Expect "10-4" to come out "10 for" and names to be wrong outright. The transcripts
are good enough to **find** a call; the audio is the record of what was said. Nothing here is an
official record, and it should not be treated as one.

## Notes on the OpenMHz API

Findings from probing the live API, recorded here because they constrain the design:

- `GET https://api.openmhz.com/oxfmswin/calls` is **CORS-open to any origin**, including the opaque
  `null` origin a `file://` page gets. This is what makes the app work as a local file.
- `GET https://api.openmhz.com/oxfmswin/talkgroups` is **not** CORS-open to third-party origins.
  The talkgroup roster is therefore baked into the page. It changes rarely, but it can go stale.
- `/calls` returns only the **latest 50 calls**, and `time`/`direction` query parameters on it do
  nothing. History lives at a different path: `GET /oxfmswin/calls/older?time=<epoch_ms>` returns the
  50 calls immediately before that moment, and `/calls/newer?time=<epoch_ms>` walks the other way.
  Page backwards by passing the oldest timestamp you already hold. Both are CORS-open like `/calls`.
- **Retention is roughly 30 days.** A request anchored 30 days back returns calls; 33 days back
  returns an empty array. Audio for 30-day-old calls still streams, so the archive is genuinely
  listenable and not just an index.
- Both the API and the audio host sit behind Cloudflare, which challenges non-browser clients.
  `curl` gets a 403 from `api.openmhz.com`; real browsers pass. The **media** host does not
  challenge `curl` at all, which is what makes a plain server-side proxy viable.
- The media host sends **no CORS header**. Audio therefore plays but cannot be read by script,
  which is the entire reason `proxy/` exists.
- The media host **rate-limits bursts**: roughly thirty rapid requests starts returning `429`,
  and it stays unhappy for a cooldown afterwards even once you stop. Measured from the page,
  a steady ~400 ms cadence sustains fine. The indexer paces itself, widens the gap when it is
  pushed back, and stands down entirely after repeated refusals rather than grinding. Retrying
  harder makes it strictly worse.

## Why this isn't a Claude Artifact

Claude Artifacts run under a Content Security Policy that blocks all outbound `fetch`/XHR and all
external media. Both the call feed and the `.m4a` audio are cross-origin, so the app cannot function
in that sandbox. It needs to run as an ordinary web page. Transcript search adds a second reason:
it loads model weights from a CDN and spins up a Worker, neither of which that sandbox allows.

## Credits

Call data and audio come from OpenMHz, fed by a volunteer-run receiver. Gaps and outages are normal.
Encrypted talkgroups never appear.
