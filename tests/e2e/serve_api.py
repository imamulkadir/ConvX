"""Disposable real API and native negative conversion for browser UI tests only."""

import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
os.environ["CONVX_API_TOKENS"] = json.dumps({"alice": "a" * 40})

import uvicorn  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from conftest import docx_bytes  # noqa: E402
from converter.context import ProcessingContext  # noqa: E402
from converter.pdf_export.libreoffice import LibreOfficeProvider  # noqa: E402
from converter.revisions.accept import accept_revisions  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from workers.tasks.admission import admit_document  # noqa: E402


def main():
    evidence = ROOT / "var/stage9"
    evidence.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="api-", dir=evidence) as directory:
        root = Path(directory)
        renderer = Path(
            os.environ.get("CONVX_TEST_LIBREOFFICE", ROOT / ".tools/libreoffice/program/soffice.com")
        )
        settings = Settings(
            _env_file=None,
            auth_mode="token",
            api_tokens={"alice": "a" * 40},
            storage_root=root / "storage",
            database_url=f"sqlite:///{root / 'jobs.db'}",
            auto_create_schema=True,
            redis_url="redis://127.0.0.1:1/0",
            libreoffice_executable=renderer if renderer.is_file() else None,
        )
        application = create_app(settings)
        seed = {"native_preview": False}
        with TestClient(application) as client:
            client.headers["Authorization"] = "Bearer " + "a" * 40
            response = client.post(
                "/api/v1/conversions", files={"files": ("native-review.docx", docx_bytes())}
            )
            job = response.json()["jobs"][0]
            if renderer.is_file():
                source = root / "source.docx"
                source.write_bytes(docx_bytes())
                accepted = root / "accepted.docx"
                accept_revisions(source, accepted)
                reference = LibreOfficeProvider(renderer).render(
                    accepted, root / "baseline", ProcessingContext()
                )
                shutil.copyfile(
                    reference.path, application.state.storage.directory(job["id"]) / "reference.pdf"
                )
            admit_document(job["id"], settings)
            result = client.get(f"/api/v1/conversions/{job['id']}/validation").json()
            assert not result["complete"]
            seed.update(
                id=job["id"], native_preview=renderer.is_file(), diagnostics=result.get("diagnostics")
            )
        evidence = ROOT / "var/stage9"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "ui-seed.json").write_text(json.dumps(seed), encoding="utf-8")
        uvicorn.run(
            application,
            host="127.0.0.1",
            port=int(os.environ.get("CONVX_UI_API_PORT", "8766")),
            access_log=False,
            log_level="warning",
        )


if __name__ == "__main__":
    main()
