from __future__ import annotations

import json
from pathlib import Path

from normalizer.models import BatchResult


def build_report_dict(result: BatchResult) -> dict:
    files: dict[str, dict] = {}
    for record in result.records:
        entry = dict(record.measurements)
        entry["warnings"] = record.warnings
        if record.error:
            entry["error"] = record.error
        files[record.source_path.name] = entry
    return {
        "config": result.config_snapshot,
        "reference": result.reference,
        "files": files,
    }


def write_report(result: BatchResult, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(build_report_dict(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
