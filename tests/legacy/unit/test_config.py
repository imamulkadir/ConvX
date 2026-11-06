import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_default_fails_closed(monkeypatch):
    monkeypatch.delenv("CONVX_API_TOKENS", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, api_tokens={})


@pytest.mark.parametrize(
    "overrides",
    [
        {"api_tokens": {"a": "short"}},
        {"api_tokens": {"a": "x" * 40, "b": "x" * 40}},
        {"environment": "production", "auth_mode": "local"},
        {"environment": "production", "auto_create_schema": True},
        {"environment": "production", "database_url": "sqlite:///file.db"},
        {"redis_url": "memory://"},
        {"max_request_bytes": 1024},
    ],
)
def test_invalid_config(settings, overrides):
    data = settings.model_dump()
    data.update(overrides)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **data)


def test_settings_repr_hides_secrets(settings):
    from conftest import TOKEN_A

    assert TOKEN_A not in repr(settings)
    assert "sqlite:///" not in repr(settings)
