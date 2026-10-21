from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone


def format_money(value: Decimal | int | float | None) -> str:
    """Million EUR with thousands separator: 4820 -> "4,820", 12.5 -> "12.50"."""
    if value is None:
        return ""
    value = Decimal(value)
    if value == value.to_integral_value():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def format_deadline(value: date | None) -> str:
    """Deadlines are shown as DD.MM.YYYY."""
    return value.strftime("%d.%m.%Y") if value else ""


def format_timestamp(value: datetime | None) -> str:
    """Comments/updates are shown as `14 Mar 2026, 09:12` (UTC)."""
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%d %b %Y, %H:%M")
