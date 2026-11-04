#!/usr/bin/env python3
"""One-time helper: get the YouTube refresh token for the "Claude news YouTube" workflow.

Run on your own computer (Python 3, no packages needed):
  python3 yt_auth.py CLIENT_ID CLIENT_SECRET
A browser opens; sign in with the Google account that owns the CISSP YouTube channel and allow access.
The script prints the refresh token: save it as the repo secret YT_REFRESH_TOKEN
(with CLIENT_ID as YT_CLIENT_ID and CLIENT_SECRET as YT_CLIENT_SECRET).
"""
import http.server, json, sys, urllib.parse, urllib.request, webbrowser

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
PORT = 8765


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cid, sec = sys.argv[1], sys.argv[2]
    redirect = f"http://127.0.0.1:{PORT}/"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent"})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got["code"] = (q.get("code") or [""])[0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b"Done. You can close this tab and go back to the terminal.")

        def log_message(self, *a):
            pass

    print("Opening:", url)
    webbrowser.open(url)
    http.server.HTTPServer(("127.0.0.1", PORT), H).handle_request()
    if not got.get("code"):
        sys.exit("No code received.")
    body = urllib.parse.urlencode({"code": got["code"], "client_id": cid, "client_secret": sec,
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    tok = json.loads(urllib.request.urlopen("https://oauth2.googleapis.com/token", body).read())
    print("\nYT_REFRESH_TOKEN =", tok.get("refresh_token") or f"(none returned: {tok})")


if __name__ == "__main__":
    main()
