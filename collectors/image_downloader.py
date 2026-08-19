"""Image downloading with deterministic naming (skills.md sections 15, 16)."""

import os

import requests

from core.logger import get_logger
from utils.hashing import image_filename

logger = get_logger("collectors")


def download_image(url: str, filename: str, headers: dict = None,
                   timeout: int = 20, max_bytes: int = 10485760) -> bool:
    try:
        response = requests.get(
            url,
            headers=headers or {},
            timeout=timeout,
            stream=True,
        )

        if response.status_code != 200:
            logger.warning("image download %s -> HTTP %s", url,
                           response.status_code)
            return False

        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            logger.warning("image download %s -> not an image (%s)", url,
                           content_type)
            return False

        total = 0
        with open(filename, "wb") as f:
            for chunk in response.iter_content(1024):
                if not chunk:
                    continue
                total += len(chunk)
                if max_bytes and total > max_bytes:
                    logger.warning("image download %s -> size limit", url)
                    return False
                f.write(chunk)

        return True
    except requests.RequestException as exc:
        logger.warning("image download failed for %s: %s", url, exc)
        return False


class ImageDownloader:
    def __init__(self, headers: dict = None, timeout: int = 20,
                 max_bytes: int = 10485760):
        self.headers = headers
        self.timeout = timeout
        self.max_bytes = max_bytes

    def download(self, url: str, image_dir: str) -> str:
        filename = os.path.join(image_dir, image_filename(url))
        if os.path.exists(filename):
            return filename
        ok = download_image(
            url,
            filename,
            headers=self.headers,
            timeout=self.timeout,
            max_bytes=self.max_bytes,
        )
        return filename if ok else ""
