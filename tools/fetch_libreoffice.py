"""Fetch the pinned free Windows renderer MSI; extraction is a separate explicit step."""

from __future__ import annotations

import hashlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

VERSION = "26.8.2"
NAME = f"LibreOffice_{VERSION}_Win_x86-64.msi"
URL = f"https://download.documentfoundation.org/libreoffice/stable/{VERSION}/win/x86_64/{NAME}"
# Published by The Document Foundation in the HTTPS .meta4 and .mirrorlist.
SHA256 = "ff4b911403b67ee9e6249f820f9782c44bb32c94fdaa45b0da53a8e419e5307a"
SIZE = 375934976


def main() -> None:
    directory = Path(__file__).resolve().parents[1] / ".tools/downloads"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / NAME
    if not target.exists():
        part = target.with_suffix(".part")
        mirror = "https://mirror.freedif.org/TDF/libreoffice/stable/26.8.2/win/x86_64/" + NAME
        chunk_size = 4 * 1024 * 1024

        def fetch(index):
            start, end = index * chunk_size, min((index + 1) * chunk_size, SIZE) - 1
            request = urllib.request.Request(mirror, headers={"Range": f"bytes={start}-{end}"})
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed HTTPS vendor-listed mirror
                        if (
                            response.status != 206
                            or response.headers.get("Content-Range") != f"bytes {start}-{end}/{SIZE}"
                        ):
                            raise RuntimeError("Mirror did not honor bounded range")
                        data = response.read(end - start + 2)
                    if len(data) != end - start + 1:
                        raise RuntimeError("Incomplete download range")
                    return data
                except Exception:
                    if attempt == 2:
                        raise

        with ThreadPoolExecutor(max_workers=8) as executor, part.open("wb") as output:
            count = 0
            chunks = (SIZE + chunk_size - 1) // chunk_size
            for offset in range(0, chunks, 8):
                for data in executor.map(fetch, range(offset, min(offset + 8, chunks))):
                    output.write(data)
                    count += len(data)
                    if count % (32 * 1024 * 1024) < len(data):
                        print(f"Downloaded {count // (1024 * 1024)} MiB", flush=True)
        part.replace(target)
    with target.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if target.stat().st_size != SIZE or digest != SHA256:
        raise RuntimeError("Renderer package integrity check failed; do not execute it")
    print(f"Verified {target.name}: {digest}", flush=True)


if __name__ == "__main__":
    main()
