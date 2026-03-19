"""Entry Point: Background scheduler for automatic daily backups."""

import logging
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def init_scheduler(backup_fn: Callable, hour: int = 23, minute: int = 0):
    """Start the background scheduler with the given backup function.

    Args:
        backup_fn: The function to call on schedule (e.g., container.backup_service.run_full_backup)
        hour: Hour to run daily (24h format)
        minute: Minute to run daily
    """
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        func=backup_fn,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_backup",
        name="Daily PostgreSQL Backup",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — daily backup at %02d:%02d", hour, minute)


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
