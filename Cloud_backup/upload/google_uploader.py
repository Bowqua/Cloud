import json
import os
import uuid
import requests

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
        "Content-Type: application/json; charset=utf-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--".encode("utf-8")

    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    response = requests.post(url, headers=headers, data=body)
    response.raise_for_status()

    return response.json()


def create_folder_google_drive(name: str, parent_id: str, access_token: str) -> str:
    payload = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        payload["parents"] = [parent_id]

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    response = requests.post("https://www.googleapis.com/drive/v3/files", headers=headers, json=payload)
    response.raise_for_status()

    return response.json()["id"]


def sync_directory_to_drive(local_directory: str, parent_id: str, access_token: str):
    folder_map = {local_directory: parent_id}
    for root, directories, files in os.walk(local_directory):
        current_parent = folder_map[root]

        for dir in directories:
            local_subdirectory = os.path.join(root, dir)
            new_folder_id = create_folder_google_drive(dir, current_parent, access_token)
            folder_map[local_subdirectory] = new_folder_id

        for file_name in files:
            local_path = os.path.join(root, file_name)
            upload_file_to_google_drive(local_path, current_parent, access_token)
