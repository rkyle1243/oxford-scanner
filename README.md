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

No build step, no dependencies, no backend. Open `index.html` directly or serve it anywhere static.

## Notes on the OpenMHz API

Findings from probing the live API, recorded here because they constrain the design:

- `GET https://api.openmhz.com/oxfmswin/calls` is **CORS-open to any origin**, including the opaque
  `null` origin a `file://` page gets. This is what makes the app work as a local file.
- `GET https://api.openmhz.com/oxfmswin/talkgroups` is **not** CORS-open to third-party origins.
  The talkgroup roster is therefore baked into the page. It changes rarely, but it can go stale.
- `/calls` returns only the **latest 50 calls**. The `time` and `direction` query parameters had no
  observable effect when tested, so there is no history paging — the page accumulates its own
  history while it runs.
- Both the API and the audio host sit behind Cloudflare, which challenges non-browser clients.
  `curl` gets a 403; real browsers pass. Any server-side proxy has to account for this.

## Why this isn't a Claude Artifact

Claude Artifacts run under a Content Security Policy that blocks all outbound `fetch`/XHR and all
external media. Both the call feed and the `.m4a` audio are cross-origin, so the app cannot function
in that sandbox. It needs to run as an ordinary web page.

## Credits

Call data and audio come from OpenMHz, fed by a volunteer-run receiver. Gaps and outages are normal.
Encrypted talkgroups never appear.
