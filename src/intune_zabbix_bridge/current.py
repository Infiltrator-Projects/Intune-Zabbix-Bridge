#!/usr/bin/env python3
"""Shipped collector entry point using the current Intune reporting framework."""

from __future__ import annotations

from typing import Any

from . import hardened
from . import ring_reports


def install_current_ring_source() -> None:
    """Bind hardened fleet/reboot logic to the current update-ring report source."""
    hardened.fetch_ring_targets = ring_reports.fetch_ring_targets  # type: ignore[assignment]
    hardened.parse_ring_targets = ring_reports.parse_ring_targets  # type: ignore[assignment]


def main(argv: list[str] | None = None) -> int:
    install_current_ring_source()
    return hardened.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
