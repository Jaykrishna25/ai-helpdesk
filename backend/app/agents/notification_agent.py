"""Agent 9 - Email/Multi-channel Notification. Queues messages; a worker (or
Amazon SES via boto3) delivers them. Demo persists to notifications table."""
import datetime as dt
from .base import BaseAgent, AgentContext
from ..models import Notification
from ..config import settings

class NotificationAgent(BaseAgent):
    name = "NotificationAgent"
    def send(self, db, user_id, user_type, subject, message, ticket_id=None, channel="email"):
        n = Notification(user_id=user_id, user_type=user_type, channel=channel,
                         subject=subject, message=message, ticket_id=ticket_id,
                         status="queued")
        db.add(n); db.flush()
        if settings.NOTIFY_BACKEND == "ses":
            self._ses_send(user_id, subject, message)   # boto3 in prod
        n.status = "sent"; n.sent_at = dt.datetime.utcnow()
        db.flush()
        return n

    def _ses_send(self, to, subject, body):  # pragma: no cover (prod path)
        import boto3
        boto3.client("ses").send_email(
            Source=settings.__dict__.get("SES_FROM", "helpdesk@univ.edu"),
            Destination={"ToAddresses": [to]},
            Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}})
