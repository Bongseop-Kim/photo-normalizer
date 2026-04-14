from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from normalizer.models import BatchResult

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_preview(
    result: BatchResult,
    output_path: Path,
    input_dir: Path,
    output_dir: Path,
) -> None:
    resolved_input = input_dir.resolve()
    resolved_output_dir = output_dir.resolve()
    resolved_preview_parent = output_path.parent.resolve()
    items = []
    for record in result.records:
        try:
            source_rel = record.source_path.resolve().relative_to(resolved_input)
        except ValueError:
            source_rel = Path(record.source_path.name)
        normalized_path = resolved_output_dir / source_rel
        items.append(
            {
                "filename": record.source_path.name,
                "normalized_rel": os.path.relpath(normalized_path, resolved_preview_parent),
                "original_rel": os.path.relpath(
                    record.source_path.resolve(), resolved_preview_parent
                ),
                "measurements": record.measurements,
                "warnings": record.warnings,
                "error": record.error,
            }
        )

    success_items = [item for item in items if not item["error"]]
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml", "j2")),
    )
    template = env.get_template("preview.html.j2")
    html = template.render(
        items=items,
        success_items=success_items,
        items_json=success_items,
    )
    output_path.write_text(html, encoding="utf-8")
