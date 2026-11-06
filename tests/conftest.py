from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOKEN_A = "a" * 40
TOKEN_B = "b" * 40


@pytest.fixture(autouse=True)
def isolated_worker_environment(monkeypatch):
    monkeypatch.setenv("CONVX_API_TOKENS", json.dumps({"alice": TOKEN_A, "bob": TOKEN_B}))


def docx_bytes(extra: dict[str, bytes] | None = None) -> bytes:
    parts = {
        "[Content_Types].xml": b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Disclosure text</w:t></w:r></w:p></w:body></w:document>',
    }
    parts.update(extra or {})
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return output.getvalue()


@pytest.fixture
def settings(tmp_path):
    from app.core.config import Settings

    return Settings(
        _env_file=None,
        api_tokens={"alice": TOKEN_A, "bob": TOKEN_B},
        storage_root=tmp_path / "storage",
        database_url=f"sqlite:///{tmp_path / 'jobs.db'}",
        auto_create_schema=True,
        redis_url="redis://127.0.0.1:1/0",
    )


@pytest.fixture
def client(settings):
    from app.main import create_app
    from fastapi.testclient import TestClient

    with TestClient(create_app(settings), raise_server_exceptions=False) as connection:
        connection.headers["Authorization"] = f"Bearer {TOKEN_A}"
        yield connection


@pytest.fixture
def fixture_docx():
    return (ROOT / "tests/fixtures/06749LWD4_prelim_prospectus_automated.docx").read_bytes()


def upload_one(client, payload=None, **kwargs):
    response = client.post(
        "/api/v1/conversions", files={"files": ("filing.docx", payload or docx_bytes())}, **kwargs
    )
    assert response.status_code == 202, response.text
    return response.json()["jobs"][0]
