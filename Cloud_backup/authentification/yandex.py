import json
import threading
import urllib.parse
import webbrowser
import config
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

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


def start_yandex_auth(callback):
    def flow():
        auth_url = (
            f"https://oauth.yandex.ru/authorize?"
            f"response_type=code&client_id={config.YANDEX_CLIENT_ID}"
            f"&scope=cloud_api:disk.read_write"
        )

        code = get_oauth_code(auth_url)
        if not code:
            return

        token_response = requests.post(
            "https://oauth.yandex.ru/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": config.YANDEX_CLIENT_ID,
                "client_secret": config.YANDEX_CLIENT_SECRET
            }
        )

        token_response.raise_for_status()
        token = token_response.json()["access_token"]

        data = {}
        try:
            data = json.load(open(config.TOKENS_FILE))
        except:
            pass

        data["yandex"] = token
        with open(config.TOKENS_FILE, "w") as f:
            json.dump(data, f)

        callback(token)
    threading.Thread(target=flow, daemon=True).start()
