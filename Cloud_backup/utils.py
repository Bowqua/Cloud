import os
import shutil
import tempfile
import time, requests
import zipfile

def retry(max_attempts=4, backoff_factor=1.5, allowed_exceptions=(requests.exceptions.RequestException,)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = 1
            for i in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions:
                    if i == max_attempts - 1:
                        raise
                    time.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator


def compress_path(path: str) -> str:
    name = os.path.basename(path.rstrip(os.sep))
    root, ext = os.path.splitext(name)
    temp_dir = tempfile.gettempdir()

    if os.path.isfile(path):
        archive_path = os.path.join(temp_dir, f"{root}.zip")
        with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(path, arcname=name)
    else:
        archive_base = os.path.join(temp_dir, root)
        archive_path = shutil.make_archive(base_name=archive_base, format="zip", root_dir=path)

    return archive_path
