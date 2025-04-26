import os
import requests

def get_yandex_upload_url(remote_path: str, access_token: str) -> str:
    headers = {"Authorization": f"OAuth {access_token}"}
    params = {"path": remote_path, "overwrite": "true"}
    response = requests.get("https://cloud-api.yandex.net/v1/disk/resources/upload", headers=headers, params=params)
    response.raise_for_status()

    return response.json()["href"]


def upload_file_to_yandex_disk(local_path: str, remote_path: str, access_token: str):
    upload_url = get_yandex_upload_url(remote_path, access_token)
    with open(local_path, "rb") as f:
        response = requests.put(upload_url, data=f)
        response.raise_for_status()


def create_folder_on_yandex(remote_path: str, access_token: str):
    headers = {"Authorization": f"OAuth {access_token}"}
    params = {"path": remote_path}
    response = requests.put("https://cloud-api.yandex.net/v1/disk/resources", headers=headers, params=params)

    if response.status_code not in (201, 409):
        response.raise_for_status()


def sync_directory_to_yandex(local_directory: str, remote_directory: str, access_token: str):
    create_folder_on_yandex(remote_directory, access_token)
    for root, directories, files in os.walk(local_directory):
        relative_path = os.path.relpath(root, local_directory)
        current_remote = remote_directory if relative_path == '.' else f"{remote_directory}/{relative_path}"

        for directory in directories:
            create_folder_on_yandex(f"{current_remote}/{directory}", access_token)

        for file_name in files:
            local_path = os.path.join(root, file_name)
            remote_path = f"{current_remote}/{file_name}"
            upload_file_to_yandex_disk(local_path, remote_path, access_token)