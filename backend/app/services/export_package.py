import csv
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.models import (
    CaptureJobResult,
    CaptureRunResult,
    ExportCaptureResultResponse,
    ExportFormat,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = BACKEND_ROOT / "data" / "exports"

BASE_COLUMNS = [
    "decision",
    "priority",
    "score",
    "title",
    "company",
    "location",
    "work_mode",
    "parser_confidence",
    "reasons",
    "warnings",
    "missing_information",
    "matched_positive_keywords",
    "matched_risk_keywords",
    "source_url",
    "errors",
]


def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _join(values: list[str] | None) -> str:
    return "; ".join(values or [])


def _relative_to_backend(path: Path) -> str:
    return path.resolve().relative_to(BACKEND_ROOT).as_posix()


def _ensure_export_dir(export_id: str) -> Path:
    export_dir = (EXPORT_ROOT / export_id).resolve()
    export_root = EXPORT_ROOT.resolve()
    if export_root not in export_dir.parents and export_dir != export_root:
        raise ValueError("Export path escaped the configured export root.")

    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _flatten_result(result: CaptureJobResult, include_raw_text: bool) -> dict[str, Any]:
    job = result.parsed_job
    decision = result.decision
    row: dict[str, Any] = {
        "decision": decision.decision if decision else "",
        "priority": decision.priority if decision else "",
        "score": decision.score if decision else "",
        "title": job.title if job else "",
        "company": job.company if job else "",
        "location": job.location if job else "",
        "work_mode": job.work_mode if job else "",
        "parser_confidence": job.parser_confidence if job else "",
        "reasons": _join(decision.reasons if decision else []),
        "warnings": _join(decision.warnings if decision else []),
        "missing_information": _join(decision.missing_information if decision else []),
        "matched_positive_keywords": _join(decision.matched_positive_keywords if decision else []),
        "matched_risk_keywords": _join(decision.matched_risk_keywords if decision else []),
        "source_url": result.raw_job.source_url or (job.source_url if job else ""),
        "errors": _join(result.errors),
    }
    if include_raw_text:
        row["raw_text"] = result.raw_job.raw_text
    return row


def _json_payload(capture_result: CaptureRunResult, include_raw_text: bool) -> dict[str, Any]:
    payload = _model_to_dict(capture_result)
    if include_raw_text:
        return payload

    for result in payload["results"]:
        result["raw_job"]["raw_text"] = ""
        if result.get("parsed_job"):
            result["parsed_job"]["description"] = ""
    return payload


def _write_json(path: Path, capture_result: CaptureRunResult, include_raw_text: bool) -> None:
    path.write_text(
        json.dumps(_json_payload(capture_result, include_raw_text), indent=2),
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], include_raw_text: bool) -> None:
    columns = BASE_COLUMNS + (["raw_text"] if include_raw_text else [])
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _autosize_columns(sheet: Worksheet) -> None:
    for column_cells in sheet.columns:
        header = column_cells[0]
        if header.column_letter is None:
            continue
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[header.column_letter].width = min(max(max_length + 2, 12), 48)


def _write_xlsx(path: Path, rows: list[dict[str, Any]], include_raw_text: bool) -> None:
    columns = BASE_COLUMNS + (["raw_text"] if include_raw_text else [])
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Capture Review"
    sheet.append(columns)

    for row in rows:
        sheet.append([row.get(column, "") for column in columns])

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    _autosize_columns(sheet)
    workbook.save(path)


def export_capture_result(
    capture_result: CaptureRunResult,
    export_format: ExportFormat,
    include_raw_text: bool = False,
) -> ExportCaptureResultResponse:
    export_id = f"export_{uuid4().hex}"
    export_dir = _ensure_export_dir(export_id)
    rows = [_flatten_result(result, include_raw_text) for result in capture_result.results]
    warnings: list[str] = []

    suffix = export_format
    path = export_dir / f"{capture_result.run_id}.{suffix}"
    if export_format == "json":
        _write_json(path, capture_result, include_raw_text)
    elif export_format == "csv":
        _write_csv(path, rows, include_raw_text)
    elif export_format == "xlsx":
        _write_xlsx(path, rows, include_raw_text)
    else:  # pragma: no cover - Pydantic validates this before service entry.
        raise ValueError(f"Unsupported export format: {export_format}")

    if not include_raw_text:
        warnings.append("Raw job text was excluded from the export.")

    return ExportCaptureResultResponse(
        export_id=export_id,
        status="completed",
        files=[_relative_to_backend(path)],
        warnings=warnings,
    )
