# oxfmswin-audio-proxy

A ~20-line Cloudflare Worker whose entire job is to add one HTTP header.

## Why it's needed

`media*.openmhz.com` serves call audio to an `<audio>` element without complaint, but
sends no `Access-Control-Allow-Origin` header. That distinction matters:

| Operation | Works? |
|---|---|
| `<audio src="…openmhz.com/….m4a">` — play it | yes |
| `fetch()` the same URL and read the bytes | **no** — blocked by CORS |
| `createMediaElementSource()` on that audio | **no** — tainted, returns silence |

Transcribing needs the samples, not just playback, so the scanner's search feature
cannot work against the media host directly. This Worker fetches the same public file
server-side (where CORS does not apply) and re-serves it with the missing header.

It stores nothing, logs nothing, transcribes nothing, and refuses any URL that is not
`https://*.openmhz.com`.

## Deploy

```bash
cd proxy
npx wrangler login
npx wrangler deploy
```

Wrangler prints a URL like `https://oxfmswin-audio-proxy.<you>.workers.dev`. Paste that
into the scanner under **Search traffic → Settings → proxy URL** and press **Test**.

The free Workers plan allows 100,000 requests/day — one request per call transcribed,
and transcripts are cached locally forever, so a normal amount of searching stays far
inside it.

## URL shapes

The page appends `?u=<encoded media url>`. If you front this with something that wants a
different shape, put `{url}` in the proxy URL you paste into the page and it will be
substituted instead:

```
https://example.com/fetch?target={url}
```

## Rate limiting

OpenMHz's media host rate-limits bursts — roughly thirty rapid requests is enough to
start collecting `429`s, after which it stays unhappy for a while. The Worker passes
those statuses straight through and the page paces itself and backs off in response,
which is why indexing a long range is deliberately unhurried. Do not "fix" this by
retrying harder in the Worker.
