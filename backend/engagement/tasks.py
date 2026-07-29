from celery import shared_task
from django.utils import timezone

from .models import Notification


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def deliver_notification(self, notification_id: str) -> None:  # type: ignore[no-untyped-def]
    """Provider adapters are deliberately isolated here; currently records in-app delivery."""
    notification = Notification.objects.get(pk=notification_id)
    if notification.status != Notification.Status.PENDING:
        return
    notification.status = Notification.Status.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at", "updated_at"])

