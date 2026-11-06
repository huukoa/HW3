"""In-memory Excel import; accepts editable project template or relevant lecture examples."""
from __future__ import annotations

import io
import re
import zipfile
from copy import deepcopy
from typing import Any

from openpyxl import load_workbook

from inventory_solver.examples import EXAMPLES, FIELDS, ITEM_FIELDS
from inventory_solver.distributions import PARAMETERS, DISTRIBUTIONS
from inventory_solver.schema import ModelInputError
from inventory_solver.numeric_input import parse_numeric

MAX_EXCEL_BYTES = 2_000_000


def _safe_scalar(value: Any, field: str) -> float:
    if value is None:
        raise ModelInputError(
            f"Excel field {field!r} is empty or is an Excel formula without a cached value. "
            "Enter a number or write an arithmetic expression as plain text."
        )
    # Normal numbers or literal text expressions are accepted. Excel workbook
    # formula cells are NOT executed or evaluated; data_only reads their cache.
    return parse_numeric(value, field=f"Excel field {field!r}")


def _template_sheet(workbook: Any, model: str) -> dict:
    source = workbook[model]
    rows = list(source.iter_rows(min_row=1, max_row=80, max_col=2, values_only=True))
    expected = {key for key, _ in FIELDS[model]}
    extras = {'distribution', 'a', 'b', 'rate', 'rho', 'lam', 'support', 'probabilities'}
    found: dict[str, Any] = {}
    for row in rows:
        name = str(row[0]).strip() if row[0] is not None else ''
        if name in expected or (model == 'HW6' and name in extras):
            value = row[1]
            if name in ('distribution', 'support', 'probabilities'):
                found[name] = str(value).strip() if value is not None else ''
            else:
                found[name] = _safe_scalar(value, name)
    kind = str(found.get('distribution', 'Normal')).title()
    if model == 'HW6' and kind != 'Normal':
        if kind not in DISTRIBUTIONS:
            raise ModelInputError(f'Unknown distribution {kind} in Excel.')
        expected -= {'mu', 'sigma'}
        expected |= {key for key, _ in PARAMETERS[kind]}
    missing = expected.difference(found)
    if missing:
        raise ModelInputError('Excel template missing: ' + ', '.join(sorted(missing)))
    if model in ITEM_FIELDS:
        name = f"Items {model}"
        if name not in workbook:
            raise ModelInputError(f"Expected the companion '{name}' worksheet.")
        sheet = workbook[name]
        header = [str(x or "").strip() for x in next(sheet.iter_rows(min_row=1, max_row=1,
                                                       max_col=20, values_only=True))]
        required = [key for key, _ in ITEM_FIELDS[model] if key not in ('mu', 'sigma')]
        if not all(k in header for k in required):
            raise ModelInputError(f"'{name}' needs columns: {', '.join(required)}")
        indices = {key: header.index(key) for key in header}
        items = []
        for record in sheet.iter_rows(min_row=2, max_row=100, max_col=len(header), values_only=True):
            if not any(x is not None and str(x).strip() for x in record):
                continue
            kind = str(record[indices['distribution']]).strip().title() if 'distribution' in indices and record[indices['distribution']] is not None else 'Normal'
            if kind not in DISTRIBUTIONS:
                raise ModelInputError(f'Unknown distribution {kind} in Excel item row.')
            item_keys = required + [key for key, _ in PARAMETERS[kind]]
            if kind == 'Normal':
                item_keys = required + ['mu', 'sigma']
            if any(k not in indices for k in item_keys):
                raise ModelInputError(f"'{name}' requires columns for {kind}: {', '.join(item_keys)}")
            item: dict[str, Any] = {}
            for key in item_keys:
                v = record[indices[key]]
                if key in ('name', 'support', 'probabilities'):
                    item[key] = str(v or '').strip()[:1000]
                else:
                    item[key] = _safe_scalar(v, key)
            if 'distribution' in indices:
                item['distribution'] = kind
            items.append(item)
        if not 2 <= len(items) <= 20:
            raise ModelInputError("Expected between 2 and 20 item rows in the companion sheet.")
        found["items"] = items
    return found


def _teacher_sheet(workbook: Any, model: str) -> dict:
    if model in ("HW1", "HW3") and "(s.Q)" in workbook:
        sheet = workbook["(s.Q)"]
        value = {"A": "B1", "r": "B2", "D": "B3", "B1": "B4",
                 "v": "B5", "muL": "B7", "sigmaL": "B8"}
        mapping = {key: _safe_scalar(sheet[cell].value, key) for key, cell in value.items()}
        if model == "HW3":
            mapping["increase_pct"] = EXAMPLES["HW3"]["increase_pct"]
        return mapping
    if model == "HW2" and "periodic" in workbook:
        sheet = workbook["periodic"]
        value = {"D": "B3", "A": "B4", "v": "B5", "r": "B6", "B3": "B7", "sigmaP": "B8"}
        mapping = {key: _safe_scalar(sheet[cell].value, key) for key, cell in value.items()}
        # Original workbook stores R,L in months. Convert months to weeks using 52 weeks/12 months.
        mapping["R"] = _safe_scalar(sheet["B1"].value, "R") * 52 / 12
        mapping["L"] = _safe_scalar(sheet["B2"].value, "L") * 52 / 12
        mapping["weeks"] = 52
        return mapping
    if model == "HW4" and "Budget" in workbook:
        sheet = workbook["Budget"]
        match = re.search(r"[-+]?\d+(?:\.\d+)?", str(sheet["G13"].value or ""))
        if not match:
            raise ModelInputError("Budget worksheet: cannot find acquisition budget in G13.")
        items = []
        for idx, col in enumerate("BCDE", 1):
            items.append({"name": f"Lecture item {idx}",
                          **{key: _safe_scalar(sheet[f"{col}{r}"].value, key)
                             for key, r in (("p",2),("v",3),("g",4),("B",5),("mu",6),("sigma",7))}})
        return {"W": float(match.group()), "items": items}
    raise ModelInputError(
        f"No '{model}' input sheet was found. Use 'Download Excel template' and edit its matching worksheet. "
        "For the instructor workbook, supported examples are (s.Q), periodic, and Budget."
    )


def read_inputs_xlsx(content: bytes, model: str) -> tuple[dict, str]:
    if not isinstance(content, bytes) or not content:
        raise ModelInputError("Upload a nonempty Excel .xlsx file.")
    if len(content) > MAX_EXCEL_BYTES:
        raise ModelInputError("Excel upload exceeds the 2 MB limit.")
    if not content.startswith(b"PK"):
        raise ModelInputError("Only valid .xlsx files are supported.")
    if model not in EXAMPLES:
        raise ModelInputError(f"Unknown model {model}")
    # Reject zip bombs before asking openpyxl to decompress workbook XML.
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 500 or sum(e.file_size for e in entries) > 20_000_000:
                raise ModelInputError("Workbook is too complex (compressed archive safety limit).")
    except zipfile.BadZipFile as exc:
        raise ModelInputError("Invalid Excel archive.") from exc
    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:
        raise ModelInputError("Cannot read this .xlsx workbook. Verify its integrity.") from exc
    try:
        if model in wb.sheetnames:
            data = _template_sheet(wb, model)
            description = f"Template worksheet '{model}'"
        else:
            data = _teacher_sheet(wb, model)
            description = f"Instructor worked-example worksheet for {model} (not the Homework inputs)"
        return deepcopy(data), description
    finally:
        wb.close()
