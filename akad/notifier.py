from __future__ import annotations

from akad.models.contract import DataContract
from akad.models.result import ValidationResult
from akad.notifiers.base import Notifier
from akad.notifiers.email_notifier import EmailNotifier
from akad.notifiers.webhook_notifier import WebhookNotifier

_DEFAULT_NOTIFIERS: list[Notifier] = [WebhookNotifier(), EmailNotifier()]


def dispatch_notifications(
    contract: DataContract,
    result: ValidationResult,
    notifiers: list[Notifier] | None = None,
) -> None:
    """Send breach notifications via all configured notifiers.

    Pass *notifiers* to override the default list — useful in tests to inject mocks.
    """
    active = notifiers if notifiers is not None else _DEFAULT_NOTIFIERS
    for n in active:
        n.notify(contract, result)
