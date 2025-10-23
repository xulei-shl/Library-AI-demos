# -*- coding: utf-8 -*-
"""
Output formatting module for CSV/Excel export.
Handles flattening JSON records and writing CSV files.
"""
import os
import json
from typing import Any, Dict, List

from src.core.pipeline_utils import ensure_dir


def flatten_record_for_excel(obj: Dict[str, Any]) -> Dict[str, str]:
    """
    Flatten JSON record for Excel/CSV export.

    Rules:
    - Top-level keys become table headers
    - 'series' field is reduced to 'name' only
    - Exclude all *_meta fields
    - None values become empty strings
    - Lists are joined with '|'
    - Nested dicts are serialized to compact JSON strings
    """
    rec: Dict[str, str] = {}
    for k, v in obj.items():
        if k.endswith("_meta"):
            continue
        if k == "series":
            if isinstance(v, dict):
                name = v.get("name")
                rec[k] = "" if name in (None, "null") else str(name).replace("\n", " ").strip()
            else:
                rec[k] = ""
            continue
        if v is None:
            rec[k] = ""
        elif isinstance(v, list):
            rec[k] = "|".join([str(x).replace("\n", " ").strip() for x in v])
        elif isinstance(v, dict):
            # Other nested objects are serialized to compact JSON
            rec[k] = json.dumps(v, ensure_ascii=False)
        else:
            rec[k] = str(v).replace("\n", " ").strip()
    return rec


def write_csv(records: List[Dict[str, str]], out_path: str) -> None:
    """
    Write records to CSV file without openpyxl dependency.
    Headers are computed as the union of all record keys.
    Cells are JSON-quoted to handle commas and newlines safely.
    """
    ensure_dir(os.path.dirname(out_path))
    # Compute union of all fields as headers
    headers: List[str] = sorted({hk for r in records for hk in r.keys()})
    lines: List[str] = []
    # Write header
    lines.append(",".join([json.dumps(h, ensure_ascii=False) for h in headers]))
    # Write data rows
    for r in records:
        row = []
        for h in headers:
            val = r.get(h, "")
            # Use JSON dumps to ensure safe comma and quote handling
            row.append(json.dumps(val, ensure_ascii=False))
        lines.append(",".join(row))
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))
