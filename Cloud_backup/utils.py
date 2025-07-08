import time, requests

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