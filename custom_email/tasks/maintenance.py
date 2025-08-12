# custom_email/tasks/maintenance.py

import logging
from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django_celery_results.models import TaskResult 
from custom_email.models import FetchStatus

logger = logging.getLogger(__name__)


@shared_task(name="custom_email.tasks.cleanup_old_fetch_statuses")
def cleanup_old_fetch_statuses(days=1, task_result_days=7):
    """
    Delete FetchStatus objects older than `days` days (default: 1).
    Also deletes Celery TaskResult records older than `task_result_days` (default: 7).
    """
    logger.info("🧹 Starting cleanup_old_fetch_statuses task")

    try:
        # Clean up FetchStatus
        fetch_cutoff = timezone.now() - timedelta(days=days)
        old_statuses = FetchStatus.objects.filter(finished_at__lt=fetch_cutoff)
        count = old_statuses.count()

        logger.info(f"🔍 Found {count} FetchStatus objects older than {days} day(s)")
        if count > 0:
            old_statuses.delete()
            logger.info(f"✅ Deleted {count} FetchStatus entries.")
        else:
            logger.info("📭 No FetchStatus entries to delete.")

        # Clean up old Celery Task Results
        task_cutoff = timezone.now() - timedelta(days=task_result_days)
        old_tasks = TaskResult.objects.filter(date_done__lt=task_cutoff)
        task_count = old_tasks.count()

        logger.info(f"🔍 Found {task_count} Celery TaskResult objects older than {task_result_days} day(s)")
        if task_count > 0:
            old_tasks.delete()
            logger.info(f"✅ Deleted {task_count} TaskResult entries.")
        else:
            logger.info("📭 No TaskResult entries to delete.")

    except Exception as e:
        logger.exception(f"❌ Exception during cleanup task: {e}")

