import json
from config import TOKENS_FILE

def load_tokens() -> dict:
    try:
        with open(TOKENS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_tokens(tokens: dict):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)


def get_token(service: str) -> str | None:
    return load_tokens().get(service)


def set_token(service: str, token: str):
    tokens = load_tokens()
    tokens[service] = token
    save_tokens(tokens)
