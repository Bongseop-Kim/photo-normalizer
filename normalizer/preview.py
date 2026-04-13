from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from normalizer.models import BatchResult

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_preview(
    result: BatchResult,
    output_path: Path,
    input_dir: Path,
    output_dir: Path,
) -> None:
    items = []
    for record in result.records:
        items.append(
            {
                "filename": record.source_path.name,
                "normalized_rel": record.source_path.name,
                "original_rel": f"../{record.source_path.name}",
                "measurements": record.measurements,
                "warnings": record.warnings,
                "error": record.error,
            }
        )

    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))
    template = env.get_template("preview.html.j2")
    html = template.render(items=items, items_json=json.dumps(items, ensure_ascii=False))
    output_path.write_text(html, encoding="utf-8")
