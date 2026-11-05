from __future__ import annotations

from app.core.config import Settings
from celery import Celery
from celery.signals import worker_ready, worker_shutdown


def make_celery(settings: Settings) -> Celery:
    application = Celery(
        "convx", broker=settings.redis_url.get_secret_value(), include=["workers.tasks.admission"]
    )
    application.conf.update(
        task_serializer="json",
        accept_content=["json"],
        task_ignore_result=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        broker_connection_timeout=3,
        broker_transport_options={
            "visibility_timeout": settings.processing_timeout_seconds + 60,
            "socket_timeout": 3,
            "socket_connect_timeout": 3,
        },
        task_default_queue="convx.admission",
        worker_concurrency=2,
        task_soft_time_limit=settings.processing_timeout_seconds + 10,
        task_time_limit=settings.processing_timeout_seconds + 20,
        worker_max_tasks_per_child=50,
        worker_max_memory_per_child=512 * 1024,
        task_send_sent_event=False,
        worker_send_task_events=False,
        worker_redirect_stdouts=False,
        worker_hijack_root_logger=False,
        worker_cancel_long_running_tasks_on_connection_loss=True,
    )
    return application


celery = make_celery(Settings())


@worker_ready.connect
def start_heartbeat(sender=None, **kwargs):
    from workers.heartbeat import start

    start()


@worker_shutdown.connect
def stop_heartbeat(sender=None, **kwargs):
    from workers.heartbeat import stop

    stop()
