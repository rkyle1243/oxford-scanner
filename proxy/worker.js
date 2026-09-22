/**
 * oxfmswin-audio-proxy — a Cloudflare Worker that does exactly one thing:
 * re-serve OpenMHz call audio with CORS headers so a browser page can read
 * the bytes and transcribe them locally.
 *
 * Why this exists: media*.openmhz.com serves the .m4a files happily to an
 * <audio> element, but sends no Access-Control-Allow-Origin header, so
 * fetch()/decodeAudioData() from the page are refused and Web Audio treats
 * the element as tainted. Playback works; reading the samples does not.
 * This Worker sits in the middle and adds the one header that was missing.
 * It stores nothing, transcribes nothing, and only ever talks to openmhz.com.
 *
 * Deploy:
 *   npx wrangler deploy            (see README for the 3-step version)
 * Then paste the worker URL into the scanner's AI Search settings.
 */

const ALLOWED_HOST = /(^|\.)openmhz\.com$/;

// Lock this down to your own page once deployed if you prefer; "*" is fine
// for a public read-only mirror of already-public audio.
const ALLOW_ORIGIN = "*";

const cors = {
  "Access-Control-Allow-Origin": ALLOW_ORIGIN,
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Headers": "Range, Content-Type",
  "Access-Control-Expose-Headers": "Content-Length, Content-Type, Accept-Ranges, Content-Range",
  "Access-Control-Max-Age": "86400",
  "Timing-Allow-Origin": ALLOW_ORIGIN
};

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", { status: 405, headers: cors });
    }

    const target = new URL(request.url).searchParams.get("u");
    if (!target) return new Response("Missing ?u=<openmhz media url>", { status: 400, headers: cors });

    let url;
    try { url = new URL(target); }
    catch { return new Response("Malformed url", { status: 400, headers: cors }); }

    // Only ever proxy openmhz.com. Without this the Worker is an open relay.
    if (url.protocol !== "https:" || !ALLOWED_HOST.test(url.hostname)) {
      return new Response("Refused: this proxy only serves https://*.openmhz.com", { status: 403, headers: cors });
    }

    const upstream = await fetch(url.toString(), {
      method: request.method,
      headers: { "Range": request.headers.get("Range") || "" },
      cf: { cacheEverything: true, cacheTtl: 86400 }
    });

    const headers = new Headers(cors);
    for (const h of ["content-type", "content-length", "accept-ranges", "content-range", "last-modified", "etag"]) {
      const v = upstream.headers.get(h);
      if (v) headers.set(h, v);
    }
    // The files are immutable once written, so let the browser keep them.
    headers.set("Cache-Control", "public, max-age=604800, immutable");

    return new Response(upstream.body, { status: upstream.status, headers });
  }
};
