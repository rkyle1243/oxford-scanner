#!/usr/bin/env python3
"""Local stand-in for worker.js -- same contract, for testing without deploying.
   Run: python3 proxy/local_proxy.py 8787   then use http://localhost:8787/?u=<url>"""
import sys, ssl, urllib.error, urllib.parse, urllib.request

# Verify certificates normally. macOS system Python is often installed without a
# CA bundle, in which case every fetch fails; fall back only then, and say so,
# rather than shipping a proxy that quietly never checks anything.
_CTX = ssl.create_default_context()
def _tls_broken():
    try:
        urllib.request.urlopen("https://media2.openmhz.com/", timeout=10, context=_CTX)
    except urllib.error.HTTPError:
        return False                      # TLS was fine; the status is not our problem
    except urllib.error.URLError as e:
        return isinstance(e.reason, ssl.SSLCertVerificationError)
    except Exception:
        return False
    return False

if _tls_broken():
    print("warning: no usable CA bundle; skipping certificate verification.\n"
          "         fine for local testing, never for anything else.", file=sys.stderr)
    _CTX = ssl.create_default_context()
    _CTX.check_hostname = False
    _CTX.verify_mode = ssl.CERT_NONE
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED = ("openmhz.com",)

class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
        self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Type, Accept-Ranges")
    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        t = (q.get("u") or [None])[0]
        if not t: self.send_response(400); self._cors(); self.end_headers(); return
        u = urllib.parse.urlparse(t)
        if u.scheme != "https" or not any(u.hostname == a or u.hostname.endswith("." + a) for a in ALLOWED):
            self.send_response(403); self._cors(); self.end_headers(); return
        try:
            with urllib.request.urlopen(urllib.request.Request(t, headers={"User-Agent": "Mozilla/5.0"}), timeout=20, context=_CTX) as r:
                body = r.read()
                self.send_response(200); self._cors()
                self.send_header("Content-Type", r.headers.get("Content-Type", "audio/mp4"))
                self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body)
        except Exception as e:
            self.send_response(502); self._cors(); self.end_headers()
            try: self.wfile.write(str(e).encode())
            except Exception: pass
    def log_message(self, *a): pass

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
