"""CSV and XLSX validation. A failed import does not replace working data."""

from __future__ import annotations

import io
from datetime import date
from typing import Any

import pandas as pd

MAX_BYTES = 2_000_000
REQUIRED = ("cohort_id", "yard_id", "arrival_date", "cohort_size")
OPTIONAL = (
    "pen_id",
    "mean_arrival_weight_lb",
    "sex_group",
    "source_type",
    "number_of_sources",
    "transport_duration_hours",
    "vaccination_history",
    "pen_area_per_head",
    "arrival_season",
    "respiratory_observation_count",
    "scenario_yard_offset",
)


def _reject_formulas(frame: pd.DataFrame) -> list[dict[str, Any]]:
    errors = []
    for column in frame.columns:
        series = frame[column].astype(str)
        for index, value in series.items():
            if value.startswith(("=", "+", "@")):
                errors.append({
                    "row": int(index) + 2,
                    "column": str(column),
                    "message": "Formula-like cells are rejected.",
                })
    return errors


def frame_from_upload(name: str, payload: bytes) -> pd.DataFrame:
    if len(payload) > MAX_BYTES:
        raise ValueError("File is larger than 2 MB.")
    lower = name.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(payload))
    if lower.endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(payload), engine="openpyxl")
    raise ValueError("Use a .csv or .xlsx file.")


def validate_cohort_frame(frame: pd.DataFrame) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    columns = {str(column).strip(): column for column in frame.columns}
    missing = [name for name in REQUIRED if name not in columns]
    for name in missing:
        errors.append({"row": 1, "column": name, "message": "Required column is missing."})
    errors.extend(_reject_formulas(frame))
    if missing:
        return {"ok": False, "errors": errors, "rows": [], "preview": []}
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for index, record in frame.iterrows():
        row_number = int(index) + 2
        item: dict[str, Any] = {}
        cohort_id = str(record[columns["cohort_id"]]).strip()
        if not cohort_id or cohort_id.lower() == "nan":
            errors.append({"row": row_number, "column": "cohort_id", "message": "Cohort id is blank."})
            continue
        if cohort_id in seen:
            errors.append({"row": row_number, "column": "cohort_id", "message": "Duplicate cohort id."})
        seen.add(cohort_id)
        item["cohort_id"] = cohort_id
        item["yard_id"] = str(record[columns["yard_id"]]).strip()
        try:
            item["arrival_date"] = date.fromisoformat(str(record[columns["arrival_date"]])[:10]).isoformat()
        except ValueError:
            errors.append({"row": row_number, "column": "arrival_date", "message": "Arrival date must be YYYY-MM-DD."})
            item["arrival_date"] = None
        try:
            head = int(float(record[columns["cohort_size"]]))
        except (TypeError, ValueError):
            head = 0
        if head <= 0 or head > 500:
            errors.append({"row": row_number, "column": "cohort_size", "message": "Head count must be from 1 to 500."})
        item["cohort_size"] = head
        for name in OPTIONAL:
            if name not in columns:
                continue
            value = record[columns[name]]
            if pd.isna(value) or str(value).strip().lower() in {"", "nan", "unknown", "na"}:
                item[name] = None if name != "vaccination_history" else "unknown"
            else:
                item[name] = value if not isinstance(value, float) else round(float(value), 3)
        item.setdefault("pen_id", f"{item['yard_id']}-IMP")
        item.setdefault("vaccination_history", "unknown")
        item.setdefault("source_type", "unknown")
        item.setdefault("prior_metaphylaxis_status", "unknown")
        item.setdefault("respiratory_observation_count", 0)
        item["provenance"] = "imported"
        rows.append(item)
    preview = rows[:8]
    return {"ok": not errors, "errors": errors, "rows": rows if not errors else [], "preview": preview, "row_count": len(rows)}
