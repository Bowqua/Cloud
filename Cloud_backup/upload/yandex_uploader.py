import os
import requests
from Cloud_backup.utils import retry

@retry(max_attempts=4)
def get_yandex_upload_url(remote_path: str, access_token: str) -> str:
    headers = {"Authorization": f"OAuth {access_token}"}
    params = {"path": remote_path, "overwrite": "true"}
    response = requests.get("https://cloud-api.yandex.net/v1/disk/resources/upload", headers=headers, params=params)
    response.raise_for_status()

    return response.json()["href"]


@retry(max_attempts=4)
def upload_file_to_yandex_disk(local_path: str, remote_path: str, access_token: str):
    upload_url = get_yandex_upload_url(remote_path, access_token)
    with open(local_path, "rb") as f:
        response = requests.put(upload_url, data=f)
        response.raise_for_status()


@retry(max_attempts=4)
def get_or_create_folder_on_yandex(remote_path: str, access_token: str):
    headers = {"Authorization": f"OAuth {access_token}"}
    response = requests.get("https://cloud-api.yandex.net/v1/disk/resources", headers=headers, params={"path": remote_path})
    if response.status_code == 200:
        return
    if response.status_code in (403, 409):
        return

    response = requests.put("https://cloud-api.yandex.net/v1/disk/resources", headers=headers, params={"path": remote_path})
    response.raise_for_status()


def sync_directory_to_yandex(local_directory: str, remote_directory: str, access_token: str):
    get_or_create_folder_on_yandex(remote_directory, access_token)
    for root, directories, files in os.walk(local_directory):
        relative_path = os.path.relpath(root, local_directory)
        current_remote = remote_directory if relative_path == '.' else f"{remote_directory}/{relative_path}"

        for directory in directories:
            get_or_create_folder_on_yandex(f"{current_remote}/{directory}", access_token)

        for file_name in files:
            local_path = os.path.join(root, file_name)
            remote_path = f"{current_remote}/{file_name}"
            upload_file_to_yandex_disk(local_path, remote_path, access_token)


@retry()
def list_yandex_directory(remote_path: str, access_token: str) -> list[dict]:
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {access_token}"}
    params = {"path": remote_path, "limit": 500}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 404:
        return []

    response.raise_for_status()
    data = response.json()

    return data.get("_embedded", {}).get("items", [])


@retry()
def get_yandex_download_url(remote_path: str, access_token: str) -> str:
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {access_token}"}
    params = {"path": remote_path}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()["href"]


@retry()
def download_file_from_yandex(remote_path: str, local_path: str, access_token: str):
    href = get_yandex_download_url(remote_path, access_token)
    with requests.get(href, stream=True) as response, open(local_path, "wb") as file:
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
