from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    event,
    insert,
    select,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings

metadata = MetaData()
schema = Table(
    "schema_version", metadata, Column("id", Integer, primary_key=True), Column("version", Integer)
)
owners = Table(
    "owners",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("touched", Integer, nullable=False),
)
jobs = Table(
    "jobs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("owner_id", ForeignKey("owners.id"), nullable=False),
    Column("original_filename", String(255), nullable=False),
    Column("source_sha256", String(64), nullable=False),
    Column("source_bytes", Integer, nullable=False),
    Column("state", String(32), nullable=False),
    Column("stage", String(64), nullable=False),
    Column("version", Integer, nullable=False, default=1),
    Column("attempt_id", String(36)),
    Column("attempts", Integer, nullable=False, default=0),
    Column("lease_until", Integer),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    Column("deleted_at", Integer),
    Column("cleanup_after", Integer),
    Column("cleaned_at", Integer),
    Column("diagnostic_code", String(64)),
)
Index("ix_job_owner_state", jobs.c.owner_id, jobs.c.state)
Index("ix_job_expiry", jobs.c.expires_at)
events = Table(
    "job_events",
    metadata,
    Column("job_id", ForeignKey("jobs.id"), primary_key=True),
    Column("sequence", Integer, primary_key=True),
    Column("state", String(32), nullable=False),
    Column("stage", String(64), nullable=False),
    Column("code", String(64)),
    Column("created_at", Integer, nullable=False),
)
outbox = Table(
    "dispatch_outbox",
    metadata,
    Column("job_id", ForeignKey("jobs.id"), primary_key=True),
    Column("token", String(36)),
    Column("locked_until", Integer, nullable=False, default=0),
    Column("next_attempt", Integer, nullable=False),
    Column("attempts", Integer, nullable=False, default=0),
    Column("sent_at", Integer),
)
submissions = Table(
    "submissions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("owner_id", ForeignKey("owners.id"), nullable=False),
    Column("key", String(128), nullable=False),
    Column("fingerprint", String(64), nullable=False),
    Column("response", JSON, nullable=False),
    Column("expires_at", Integer, nullable=False),
    UniqueConstraint("owner_id", "key"),
)
heartbeats = Table(
    "worker_heartbeats",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("seen_at", Integer, nullable=False),
    Column("capability", String(64), nullable=False),
)


class Database:
    def __init__(self, settings: Settings):
        url = make_url(settings.database_url.get_secret_value())
        if url.get_backend_name() == "sqlite" and url.database not in (None, ":memory:"):
            Path(url.database).resolve().parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"timeout": 15} if url.get_backend_name() == "sqlite" else {},
        )
        if self.engine.dialect.name == "sqlite":

            @event.listens_for(self.engine, "connect")
            def configure_sqlite(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")

        self.settings = settings

    def initialize(self) -> None:
        metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(schema.c.version).where(schema.c.id == 1)
            ).scalar_one_or_none()
            if existing is None:
                connection.execute(insert(schema).values(id=1, version=1))
            elif existing != 1:
                raise RuntimeError("Unsupported database schema")
        for owner in self.settings.api_tokens if self.settings.auth_mode == "token" else ["local"]:
            try:
                with self.engine.begin() as connection:
                    connection.execute(insert(owners).values(id=owner, touched=0))
            except IntegrityError:
                # A duplicate owner is expected during repeated initialization.
                with self.engine.connect() as connection:
                    if (
                        connection.execute(
                            select(owners.c.id).where(owners.c.id == owner)
                        ).scalar_one_or_none()
                        is None
                    ):
                        raise

    def check_schema(self) -> None:
        with self.engine.connect() as connection:
            if connection.execute(select(schema.c.version).where(schema.c.id == 1)).scalar_one() != 1:
                raise RuntimeError("Unsupported database schema")

    @contextmanager
    def transaction(self):
        with self.engine.begin() as connection:
            yield connection
