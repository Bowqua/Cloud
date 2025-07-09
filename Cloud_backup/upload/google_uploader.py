import json
import os
import uuid
import requests
from googleapiclient.http import MediaIoBaseDownload

from Cloud_backup.utils import retry

def upload_file_to_google_drive(local_path: str, parent_id: str, access_token: str) -> dict:
    boundary = uuid.uuid4().hex
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    }

    metadata = {"name": os.path.basename(local_path)}
    if parent_id:
        metadata["parents"] = [parent_id]

    with open(local_path, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--".encode("utf-8")

    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    response = requests.post(url, headers=headers, data=body)
    response.raise_for_status()

    return response.json()


def get_or_create_folder_google_drive(name: str, parent_id: str, access_token: str) -> str:
    headers = {"Authorization": f"Bearer {access_token}"}
    q = (
        f"name = '{name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents "
        f"and trashed = false"
    )
    response = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers=headers,
        params={"q": q, "fields": "files(id, name)", "spaces": "drive"}
    )
    response.raise_for_status()
    files = response.json().get("files", [])
    if files:
        return files[0]["id"]

    payload = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        payload["parents"] = [parent_id]
    headers["Content-Type"] = "application/json"
    response = requests.post(
        "https://www.googleapis.com/drive/v3/files",
        headers=headers,
        json=payload
    )

    # headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    # response = requests.post("https://www.googleapis.com/drive/v3/files", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["id"]


def sync_directory_to_drive(local_directory: str, parent_id: str, access_token: str):
    folder_map = {local_directory: parent_id}
    for root, directories, files in os.walk(local_directory):
        current_parent = folder_map[root]

        for dir in directories:
            local_subdirectory = os.path.join(root, dir)
            new_folder_id = get_or_create_folder_google_drive(dir, current_parent, access_token)
            folder_map[local_subdirectory] = new_folder_id

        for file_name in files:
            local_path = os.path.join(root, file_name)
            upload_file_to_google_drive(local_path, current_parent, access_token)


@retry(max_attempts=4)
def list_google_drive_files(service, folder_id="root"):
    items = []
    page_token = None
    while True:
        response = service.files().list(
            q = f"'{folder_id}' in parents and trashed = false",
            fields = "nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            pageToken = page_token,
            pageSize = 1000,
        ).execute()

        items.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return items


@retry(max_attempts=4)
def download_files_from_google_drive(service, file_id, local_path):
    request = service.files().get_media(fileId=file_id)
    with open(local_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

    return local_path


