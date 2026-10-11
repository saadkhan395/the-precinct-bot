"""Assign approved content to future publishing slots; does not publish anything."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import yaml

ROOT = Path(__file__).resolve().parents[2]
LOG = logging.getLogger("daily_precinct.scheduler")


def connect_sheet():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    client = gspread.service_account_from_dict(info)
    return client.open_by_key(os.environ["GOOGLE_SHEET_ID"])


def load_settings():
    with (ROOT / "config/settings.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def media_exists(content_id: str, content_type: str) -> bool:
    if not content_id or Path(content_id).name != content_id:
        return False
    if content_type == "image":
        p = ROOT / "output/images" / f"{content_id}.jpg"
        return p.is_file() and p.stat().st_size > 0
    if content_type == "reel":
        p = ROOT / "output/reels" / f"{content_id}.mp4"
        return p.is_file() and p.stat().st_size > 0
    if content_type == "carousel":
        folder = ROOT / "output/carousels" / content_id
        slides = list(folder.glob("slide-*.jpg")) if folder.is_dir() else []
        return len(slides) >= 3 and all(p.stat().st_size > 0 for p in slides)
    return False


def valid_for_scheduling(row: dict) -> tuple[bool, str]:
    cid = str(row.get("Content ID", "")).strip()
    kind = str(row.get("Content Type", "")).strip().lower()
    if not cid:
        return False, "missing Content ID"
    if str(row.get("Status", "")).strip() != "Approved":
        return False, "status is not Approved"
    if not re.match(r"^PASS\s*\(\d+ checks?\)$", str(row.get("Validation Result", "")).strip(), re.I):
        return False, "Validation Result is not an explicit PASS"
    if not str(row.get("Caption", "")).strip():
        return False, "missing caption"
    if kind not in {"image", "carousel", "reel"}:
        return False, f"unsupported content type: {kind}"
    if not media_exists(cid, kind):
        return False, "required media file(s) missing from repository checkout"
    return True, ""


def parse_slot(value: str, default: str) -> time:
    raw = str(value or default)
    try:
        return time.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid schedule time {raw!r}; use HH:MM (24-hour).") from exc


def candidate_slots(now: datetime, settings: dict, occupied: set[str], horizon_days: int = 21):
    sched = settings.get("scheduling", {})
    slots = sched.get("slots", {})
    # Days use Python weekday numbering: Monday=0 ... Sunday=6.
    defaults = {
        "image": [{"day": d, "time": "10:00"} for d in range(7)],
        "carousel": [{"day": d, "time": "12:00"} for d in (0, 2, 4)],
        "reel": [{"day": d, "time": "18:00"} for d in (1, 3)],
    }
    result = []
    local_day = now.date()
    for offset in range(horizon_days + 1):
        date = local_day + timedelta(days=offset)
        for kind in ("image", "carousel", "reel"):
            for slot in slots.get(kind, defaults[kind]):
                if int(slot.get("day", -1)) != date.weekday():
                    continue
                t = parse_slot(slot.get("time"), defaults[kind][0]["time"])
                dt = datetime.combine(date, t, tzinfo=now.tzinfo)
                key = dt.isoformat(timespec="minutes")
                if dt > now and key not in occupied:
                    result.append((dt, kind, key))
    result.sort(key=lambda x: x[0])
    return result


def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s")
    settings = load_settings()
    timezone_name = os.getenv("SCHEDULE_TIMEZONE") or settings.get("timezone", "America/New_York")
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz).replace(second=0, microsecond=0)
    sh = connect_sheet()
    try:
        ws = sh.worksheet("Content")
    except gspread.WorksheetNotFound:
        raise RuntimeError("Content worksheet does not exist. Generate content first.")

    headers = ws.row_values(1)
    required = ["Content ID", "Content Type", "Status", "Scheduled Time", "Validation Result", "Caption"]
    missing = [h for h in required if h not in headers]
    if missing:
        raise RuntimeError(f"Content sheet missing required columns: {missing}")
    col = {name: headers.index(name) + 1 for name in headers}
    rows = ws.get_all_records()

    occupied = set()
    for row in rows:
        raw = str(row.get("Scheduled Time", "")).strip()
        if raw:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                occupied.add(dt.astimezone(tz).isoformat(timespec="minutes"))
            except ValueError:
                LOG.warning("Ignoring unparsable existing Scheduled Time for %s", row.get("Content ID"))

    eligible = []
    for idx, row in enumerate(rows, start=2):
        if str(row.get("Status", "")).strip() != "Approved" or str(row.get("Scheduled Time", "")).strip():
            continue
        ok, reason = valid_for_scheduling(row)
        if ok:
            eligible.append((idx, row))
        else:
            LOG.warning("Not scheduling %s: %s", row.get("Content ID", "<unknown>"), reason)

    slots = candidate_slots(now, settings, occupied, int(settings.get("scheduling", {}).get("horizon_days", 21)))
    # Match each approved item to the next available slot for its content type.
    assigned = 0
    for sheet_row, row in eligible:
        kind = str(row.get("Content Type", "")).strip().lower()
        match = next((item for item in slots if item[1] == kind), None)
        if not match:
            LOG.warning("No future %s slot available within scheduling horizon for %s", kind, row.get("Content ID"))
            continue
        dt, _, key = match
        # Store explicit ISO timestamp with offset so the timezone is unambiguous.
        ws.update_cell(sheet_row, col["Scheduled Time"], dt.isoformat(timespec="minutes"))
        ws.update_cell(sheet_row, col["Status"], "Scheduled")
        slots.remove(match)
        occupied.add(key)
        assigned += 1
        LOG.info("Scheduled %s (%s) for %s", row.get("Content ID"), kind, dt.isoformat(timespec="minutes"))

    LOG.info("Scheduling run complete: %d assigned; %d eligible; timezone=%s", assigned, len(eligible), timezone_name)


if __name__ == "__main__":
    main()
