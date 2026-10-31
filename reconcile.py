#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py

Rules (see README):
  * A payment can be attempted several times under one txn_id; only the
    latest attempt (by `ts`, not by position in the file) counts.
  * A payment is collected only if its latest attempt is `success`.
  * Lines that can't be read, and events without a txn_id, are ignored.
  * Amounts may arrive as numbers or as strings with thousands separators
    (e.g. "4,804.15"), so they are normalised before summing.
"""
import json
from datetime import datetime
from decimal import Decimal


def parse_ts(value):
    """Parse an ISO-8601 UTC timestamp like 2026-09-21T15:30:26Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_amount(value):
    """Turn 3533.05, 15 or "4,804.15" into an exact Decimal."""
    return Decimal(str(value).replace(",", "").strip())


# txn_id -> (timestamp, line_number, event) for the latest attempt seen so far
latest = {}

with open("payments.jsonl", encoding="utf-8") as f:
    for line_no, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # truncated / unreadable line
        if not isinstance(event, dict):
            continue

        txn_id = event.get("txn_id")
        if not txn_id:
            continue  # no txn_id: can't be matched to a payment

        # Later timestamp wins; if two attempts share a timestamp, the one
        # that appears later in the file wins.
        key = (parse_ts(event["ts"]), line_no)
        if txn_id not in latest or key > latest[txn_id][:2]:
            latest[txn_id] = (*key, event)

total = Decimal("0")
count = 0
for _, _, event in latest.values():
    if event["status"] == "success":
        total += parse_amount(event["amount"])
        count += 1

with open("expected.txt") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")