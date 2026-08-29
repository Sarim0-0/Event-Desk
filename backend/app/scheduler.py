from collections.abc import Awaitable, Callable
from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler


SEND_DUE_EVENT_REMINDERS_JOB_ID = "send_due_event_reminders"
COMPLETE_PAST_EVENTS_JOB_ID = "complete_past_events"
JOB_MISFIRE_GRACE_TIME_SECONDS = 30

ScheduledJob = Callable[[], Awaitable[None]]

scheduler = AsyncIOScheduler(timezone=timezone.utc)


def register_minutely_job(job: ScheduledJob, *, job_id: str) -> None:
    """Register one UTC minutely job, replacing an existing matching ID."""

    while scheduler.get_job(job_id) is not None:
        scheduler.remove_job(job_id)

    scheduler.add_job(
        job,
        trigger="interval",
        minutes=1,
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=JOB_MISFIRE_GRACE_TIME_SECONDS,
    )


def start_scheduler() -> None:
    """Start the embedded scheduler once for this application process."""

    if not scheduler.running:
        scheduler.start()


def shutdown_scheduler() -> None:
    """Shut down the scheduler if this process started it."""

    if scheduler.running:
        scheduler.shutdown(wait=True)
