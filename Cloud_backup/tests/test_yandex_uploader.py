import pytest
import requests
from Cloud_backup.upload.yandex_uploader import get_yandex_upload_url ,list_yandex_directory

class DummyResp:
    def __init__(self, status, json_data=None, text=""):
        self.status_code = status
        self._json = json_data or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            http_error = requests.exceptions.HTTPError(f"{self.status_code} Client Error")
            http_error.response = self
            raise http_error

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def patch_requests(monkeypatch):
    def fake_get(url, **kwargs):
        params = kwargs.get("params", {})
        if "upload" in url:
            return DummyResp(200, {"href": "http://upload.url"})
        if params.get("path") == "nope":
            return DummyResp(404)
        return DummyResp(200, {"_embedded": {"items": [{"name": "f", "type": "file"}]}})
    def fake_put():
        return DummyResp(201)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "put", fake_put)


def test_get_yandex_upload_url():
    url = get_yandex_upload_url("Backup/a.txt", "token")
    assert url == "http://upload.url"


def test_list_directory_found():
    items = list_yandex_directory("Backup", "token")
    assert isinstance(items, list)
    assert items and items[0]["name"] == "f"


def test_list_directory_not_found():
    items = list_yandex_directory("nope", "token")
    assert items == []
