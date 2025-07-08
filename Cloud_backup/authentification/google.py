import json
import threading
import urllib.parse
import webbrowser
import config
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code = params.get('code', [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<html><body><h1>You may close this window</h1></body></html>")
        self.server.auth_code = code


    def log_message(self, *args):
        return


def get_oauth_code(auth_url):
    port = 8080
    server = HTTPServer(('localhost', port), CallbackHandler)
    webbrowser.open(auth_url)
    server.handle_request()
    return getattr(server, 'auth_code', None)


def start_google_auth(callback):
    def flow():
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"response_type=code"
            f"&client_id={config.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={config.REDIRECT_URI}"
            "&scope=https://www.googleapis.com/auth/drive.file"
            "&access_type=offline"
        )

        code = get_oauth_code(auth_url)
        if not code:
            return

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "redirect_uri": config.REDIRECT_URI
            }
        )

        response.raise_for_status()
        data = response.json()
        access_token = data["access_token"]
        refresh_token = data.get("refresh_token")

        token_data = {}
        try:
            token_data = json.load(open(config.TOKENS_FILE))
        except:
            pass

        token_data["google_access"] = access_token
        token_data["google_refresh"] = refresh_token

        with open(config.TOKENS_FILE, "w") as f:
            json.dump(token_data, f)

        callback(access_token)
    threading.Thread(target=flow, daemon=True).start()
