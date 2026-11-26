"""Helpers for checking permissions on secret-bearing files."""

from __future__ import annotations

import logging
import stat
from pathlib import Path

logger = logging.getLogger(__name__)


def current_mode(path: Path) -> int | None:
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return None


def is_mode_600(path: Path) -> bool:
    return current_mode(path) == 0o600


def warn_if_insecure(path: Path, label: str) -> None:
    """Log a warning (never file contents) when a sensitive file is too open."""
    mode = current_mode(path)
    if mode is None:
        logger.warning("%s not found: %s", label, path)
        return
    if mode != 0o600:
        # Fix it when possible, but still warn the operator.
        logger.warning("%s has permissions %o (expected 600): %s", label, mode, path)
        try:
            path.chmod(0o600)
            logger.warning("%s permissions were automatically changed to 600", label)
        except OSError:
            logger.warning("Could not change permissions of %s", label)
