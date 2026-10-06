#!/usr/bin/env python3
"""Portable timezone for daily-ai-news-digest runtime timestamps.

Named IANA zones require the tzdata package so Windows hosts without a
system timezone database still resolve SKILL_TIMEZONE correctly.
"""

from __future__ import annotations

import os
from datetime import timezone as dt_timezone
from datetime import tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "UTC"
_UNSAFE_MARKERS = (";", "|", "&", "`", "$(", "\n", "\x00")


def resolve_skill_timezone(name: str | None = None) -> tzinfo:
    configured = (name if name is not None else os.environ.get("SKILL_TIMEZONE", "")).strip()
    timezone_name = configured or DEFAULT_TIMEZONE
    if any(marker in timezone_name for marker in _UNSAFE_MARKERS):
        raise ValueError("SKILL_TIMEZONE contains unsafe characters")
    if timezone_name.upper() == "UTC":
        return dt_timezone.utc
    try:
        import tzdata  # noqa: F401
    except ImportError as exc:
        raise ValueError(
            "Named SKILL_TIMEZONE values require the tzdata package. "
            "Install with: python3 -m pip install tzdata"
        ) from exc
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown SKILL_TIMEZONE: {timezone_name}") from exc
    except Exception as exc:
        raise ValueError(f"could not load SKILL_TIMEZONE {timezone_name}: {exc}") from exc


def timezone_label(tz: tzinfo | None = None) -> str:
    resolved = tz or resolve_skill_timezone()
    return getattr(resolved, "key", None) or DEFAULT_TIMEZONE
