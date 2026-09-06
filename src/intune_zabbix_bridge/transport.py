"""Lossless fleet-summary transport within Zabbix's text history budget."""

from __future__ import annotations

import base64
import json
import logging
import zlib

ZABBIX_TEXT_SAFE_BYTES = 64_000
MAX_DECODED_BYTES = 4_000_000
TRANSPORT = "intune-zabbix-zlib-v1"


def encode_summary(summary_json: str) -> str:
    """Keep small summaries readable; compress larger ones without losing rows.

    Called before any metric is sent. The entire envelope, including base64
    overhead, must fit the existing item; the widget enforces the same decoded
    size bound. Dry-run output and internal metrics remain ordinary JSON.
    """
    raw = summary_json.encode("utf-8")
    if len(raw) > MAX_DECODED_BYTES:
        raise RuntimeError(
            f"fleet summary exceeds decoded size limit ({len(raw)} bytes > "
            f"{MAX_DECODED_BYTES}); no metrics published"
        )
    if len(raw) <= ZABBIX_TEXT_SAFE_BYTES:
        return summary_json

    envelope = json.dumps({
        "transport": TRANSPORT,
        "uncompressed_bytes": len(raw),
        "data": base64.b64encode(zlib.compress(raw, level=9)).decode("ascii"),
    }, separators=(",", ":"))
    size = len(envelope.encode("utf-8"))
    if size > ZABBIX_TEXT_SAFE_BYTES:
        raise RuntimeError(
            "fleet summary is too large for safe Zabbix text storage even after "
            f"compression ({size} bytes > {ZABBIX_TEXT_SAFE_BYTES}; "
            f"{len(raw)} bytes decoded); no metrics published"
        )
    logging.getLogger("intune-zabbix-bridge").info(
        "Fleet summary transport: %d bytes JSON -> %d bytes compressed envelope",
        len(raw), size,
    )
    return envelope
