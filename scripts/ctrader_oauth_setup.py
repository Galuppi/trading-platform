"""Local OAuth helper: run the cTrader Open API consent flow entirely in the browser.

Run once (python scripts/ctrader_oauth_setup.py) whenever you need a fresh
refresh token -- e.g. after a restart if the persisted one has gone stale.
Not part of the running trading app.

What it does, all in one pass:
  1. Starts a tiny local web server on http://localhost:PORT.
  2. Opens your browser to the cTrader consent page.
  3. After you approve, cTrader redirects back to this same local server with
     an authorization code -- no more copying a code out of a dead page and
     pasting it into a terminal.
  4. The server exchanges that code for tokens and fetches your linked
     accounts, all server-side, so CTRADER_CLIENT_SECRET never reaches the
     browser -- and renders the refresh token (with a copy button) and
     account list directly on that page.
  5. The script exits automatically once the page has been served.

Nothing is written to .env automatically. Copy the refresh token from the
page into .env yourself: CTRADER_REFRESH_TOKEN=...

Uses Twisted's own web server (twisted.web), not Flask -- this keeps the
whole script on a single reactor/event loop, since it needs Twisted anyway
to talk to the cTrader API for the account lookup. Running Flask's own loop
alongside Twisted's reactor in one process would reintroduce the same
sync/async bridging complexity CTraderSession exists to solve; not worth it
for a script this small.

One-time setup: on https://connect.spotware.com/apps, add this exact
redirect URI to your app's registered list (alongside any existing ones --
this doesn't replace them):

    http://localhost:5069/oauth_callback.html

Port 5069 is arbitrary but unprivileged (avoids needing admin rights or
fighting IIS/Skype for port 80, which the old http://localhost redirect
implied). If 5069 is taken on your machine, change PORT below and update
the registered redirect URI to match.

Usage:
    python scripts/ctrader_oauth_setup.py
"""

import os
import sys
import webbrowser

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CTRADER_CLIENT_ID")
CLIENT_SECRET = os.getenv("CTRADER_CLIENT_SECRET")

PORT = 5069
REDIRECT_URI = f"http://localhost:{PORT}/oauth_callback.html"

PAGE_STYLE = """
  body {
    font-family: -apple-system, Segoe UI, Arial, sans-serif;
    background: #0f1115;
    color: #e6e6e6;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    margin: 0;
    padding: 24px 0;
  }
  .card {
    background: #1a1d24;
    border: 1px solid #2a2e37;
    border-radius: 12px;
    padding: 32px 40px;
    max-width: 640px;
    width: 90%;
  }
  h1 { font-size: 18px; margin: 0 0 16px; color: #9aa4b2; font-weight: 600; }
  h2 { font-size: 14px; margin: 24px 0 10px; color: #9aa4b2; font-weight: 600; }
  .code-box {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #0f1115;
    border: 1px solid #2a2e37;
    border-radius: 8px;
    padding: 14px 16px;
  }
  code { flex: 1; font-family: Consolas, Menlo, monospace; font-size: 13px; word-break: break-all; color: #7ee787; }
  button {
    background: #2f81f7; color: white; border: none; border-radius: 6px;
    padding: 8px 14px; font-size: 13px; cursor: pointer; white-space: nowrap;
  }
  button:hover { background: #4a90f9; }
  button.copied { background: #2ea043; }
  table { width: 100%; border-collapse: collapse; margin-top: 4px; }
  th, td { text-align: left; padding: 8px 10px; font-size: 13px; border-bottom: 1px solid #2a2e37; }
  th { color: #9aa4b2; font-weight: 600; }
  .env-line { font-family: Consolas, Menlo, monospace; font-size: 12px; color: #9aa4b2; margin-top: 8px; }
  .empty { color: #9aa4b2; font-size: 14px; }
  .hint { color: #9aa4b2; font-size: 12px; margin-top: 16px; line-height: 1.5; }
"""


def _page(title: str, body: str) -> bytes:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{title}</title>
<style>{PAGE_STYLE}</style></head>
<body><div class="card"><h1>{title}</h1>{body}</div></body></html>""".encode()


def _result_page(refresh_token: str, account_rows_html: str) -> bytes:
    body = f"""
      <div class="code-box">
        <code id="token-text">{refresh_token}</code>
        <button id="copy-btn">Copy</button>
      </div>
      <div class="env-line">CTRADER_REFRESH_TOKEN={refresh_token}</div>

      <h2>Linked trading accounts</h2>
      <table>
        <tr><th>Type</th><th>Login</th><th>ctidTraderAccountId</th></tr>
        {account_rows_html}
      </table>

      <div class="hint">
        Match the "Login" number above to the account number shown in the
        cTrader UI (e.g. 10086648), then set CTRADER_ACCOUNT_ID to its
        ctidTraderAccountId -- these are not the same number.<br><br>
        You can close this tab now.
      </div>

      <script>
        document.getElementById("copy-btn").addEventListener("click", () => {{
          navigator.clipboard.writeText({refresh_token!r}).then(() => {{
            const btn = document.getElementById("copy-btn");
            btn.textContent = "Copied";
            btn.classList.add("copied");
            setTimeout(() => {{ btn.textContent = "Copy"; btn.classList.remove("copied"); }}, 1500);
          }});
        }});
      </script>
    """
    return _page("cTrader OAuth complete", body)


def main() -> None:
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Set CTRADER_CLIENT_ID and CTRADER_CLIENT_SECRET in .env first.")
        sys.exit(1)

    from ctrader_open_api import Auth, Client, EndPoints, TcpProtocol, Protobuf
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq,
        ProtoOAGetAccountListByAccessTokenReq,
    )
    from twisted.internet import reactor
    from twisted.web.resource import Resource
    from twisted.web.server import NOT_DONE_YET, Site

    auth = Auth(CLIENT_ID, CLIENT_SECRET, redirectUri=REDIRECT_URI)

    def finish(request, body: bytes) -> None:
        request.setHeader(b"Content-Type", b"text/html; charset=utf-8")
        request.write(body)
        request.finish()
        # Give the response a moment to actually flush before tearing down.
        reactor.callLater(0.5, reactor.stop)

    class CallbackPage(Resource):
        isLeaf = True

        def render_GET(self, request):
            request.setHeader(b"Content-Type", b"text/html; charset=utf-8")

            code_values = request.args.get(b"code")
            if not code_values:
                return _page("No authorization code", "<p class='empty'>No ?code= parameter found in the URL.</p>")
            code = code_values[0].decode()

            # Single blocking HTTP call. Fine here: this is a one-shot local
            # script that serves exactly one request and exits, not a long
            # running server -- not worth threading off for that.
            token_response = auth.getToken(code)
            if not isinstance(token_response, dict) or "accessToken" not in token_response:
                return _page("Token exchange failed", f"<p class='empty'>{token_response}</p>")

            access_token = token_response["accessToken"]
            refresh_token = token_response["refreshToken"]

            self._fetch_accounts(request, access_token, refresh_token)
            return NOT_DONE_YET

        def _fetch_accounts(self, request, access_token: str, refresh_token: str) -> None:
            host = EndPoints.PROTOBUF_DEMO_HOST
            client = Client(host, EndPoints.PROTOBUF_PORT, TcpProtocol)

            def fail(context: str, failure) -> None:
                finish(request, _page(f"Failed: {context}", f"<p class='empty'>{failure}</p>"))
                client.stopService()

            def on_connected(_client) -> None:
                req = ProtoOAApplicationAuthReq(clientId=CLIENT_ID, clientSecret=CLIENT_SECRET)
                deferred = client.send(req)
                deferred.addCallbacks(on_app_authenticated, lambda f: fail("app auth", f))

            def on_app_authenticated(raw_response) -> None:
                response = Protobuf.extract(raw_response)
                if response.__class__.__name__ == "ProtoOAErrorRes":
                    fail("app auth", f"{response.errorCode}: {response.description}")
                    return
                req = ProtoOAGetAccountListByAccessTokenReq(accessToken=access_token)
                deferred = client.send(req)
                deferred.addCallbacks(on_accounts_received, lambda f: fail("account list", f))

            def on_accounts_received(raw_response) -> None:
                response = Protobuf.extract(raw_response)
                if response.__class__.__name__ == "ProtoOAErrorRes":
                    fail("account list", f"{response.errorCode}: {response.description}")
                    return

                rows = "".join(
                    f"<tr><td>{'LIVE' if a.isLive else 'DEMO'}</td>"
                    f"<td>{a.traderLogin}</td><td>{a.ctidTraderAccountId}</td></tr>"
                    for a in response.ctidTraderAccount
                ) or "<tr><td colspan='3'>No accounts found.</td></tr>"

                finish(request, _result_page(refresh_token, rows))
                client.stopService()

            def on_disconnected(_client, reason) -> None:
                pass

            client.setConnectedCallback(on_connected)
            client.setDisconnectedCallback(on_disconnected)
            client.startService()

    root = Resource()
    root.putChild(b"oauth_callback.html", CallbackPage())
    reactor.listenTCP(PORT, Site(root), interface="127.0.0.1")

    auth_uri = auth.getAuthUri(scope="trading")
    print(f"\nOpening your browser for cTrader consent...")
    print(f"If it doesn't open automatically, go to:\n\n  {auth_uri}\n")
    print(f"Waiting on http://localhost:{PORT} for the redirect...\n")
    reactor.callLater(0.5, webbrowser.open, auth_uri)

    reactor.run()


if __name__ == "__main__":
    main()
