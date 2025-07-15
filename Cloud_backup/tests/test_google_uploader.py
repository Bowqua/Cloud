import pytest
from Cloud_backup.upload.google_uploader import list_google_drive_files, download_files_from_google_drive
from googleapiclient.http import MediaIoBaseDownload

class DummyReqList:
    def __init__(self):
        self._pages = [
            {"files": [{"id": "1", "name": "a", "mimeType": "t"}], "nextPageToken": None}
        ]
    def execute(self):
        return self._pages.pop(0)


class DummyMediaRequest:
    def __init__(self, fileId):
        self.fileId = fileId


class DummyFilesService:
    def __init__(self):
        self._list = DummyReqList()
    def list(self, **kwargs):
        return self._list
    def get_media(self, fileId):
        return DummyMediaRequest(fileId)


class DummyService:
    def __init__(self):
        self.files = DummyFilesService()


@pytest.fixture(autouse=True)
def patch_media_download(monkeypatch, tmp_path):
    def fake_init(self, fh, req):
        self._fh = fh
        self._req = req
        self._done = False
    def fake_next_chunk(self):
        if not self._done:
            self._fh.write(b"data")
            self._done = True
            return ({"progress": 1.0}, True)
        return ({"progress": 1.0}, True)

    monkeypatch.setattr(MediaIoBaseDownload, "__init__", fake_init)
    monkeypatch.setattr(MediaIoBaseDownload, "next_chunk", fake_next_chunk)


def test_list_google():
    svc = DummyService()
    items = list_google_drive_files(svc, folder_id="root")
    assert isinstance(items, list)
    assert items[0]["id"] == "1"


def test_download_google(tmp_path):
    svc = DummyService()
    out = tmp_path / "out.bin"
    download_files_from_google_drive(svc, "1", str(out))
    assert out.exists()
    assert out.read_bytes() == b"data"
