from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from utils.constants import CSV_ALIASES, CSV_EXPECTED_COLUMNS


class CsvParserError(Exception):
    pass


class CsvParser:
    def __init__(self, path: Path) -> None:
        self.path = path

    def parse_all(self) -> list[dict[str, Any]]:
        from utils.file_utils import read_text_robust

        if not self.path.exists():
            raise CsvParserError(f"CSV file not found: {self.path}")

        try:
            content = read_text_robust(self.path)
        except Exception as error:
            raise CsvParserError(f"Failed to read CSV: {error}") from error

        if not content or not content.strip():
            raise CsvParserError(f"CSV file is empty: {self.path}")

        try:
            first_line = content.splitlines()[0] if content.splitlines() else ""
            delimiter = ","
            if ";" in first_line and "," not in first_line:
                delimiter = ";"
            elif "\t" in first_line and "," not in first_line:
                delimiter = "\t"

            reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
            rows = list(reader)
        except Exception as error:
            raise CsvParserError(f"Failed to parse CSV: {error}") from error

        if not rows:
            raise CsvParserError(f"CSV file has no data rows: {self.path}")

        fieldnames = reader.fieldnames or []
        headers = {header.strip().lower(): header for header in fieldnames if header}

        has_header_overlap = False
        all_expected = set(CSV_EXPECTED_COLUMNS)
        for val in CSV_ALIASES.values():
            all_expected.update(val)

        for h in headers:
            if h in all_expected:
                has_header_overlap = True
                break

        if not has_header_overlap:
            raise CsvParserError("Malformed CSV or incorrect delimiters: no expected header columns found.")

        normalized_rows = []
        for row in rows:
            normalized_row: dict[str, Any] = {}
            for column in CSV_EXPECTED_COLUMNS:
                value = self._find_value(row, headers, column)
                normalized_row[column] = self._clean_value(value)

            # Only add rows that have at least one identifier
            if normalized_row.get("name") or normalized_row.get("email") or normalized_row.get("phone"):
                normalized_rows.append(normalized_row)

        if not normalized_rows:
            raise CsvParserError("Malformed CSV: no candidate identifiers (name, email, or phone) found in any row.")

        return normalized_rows

    def parse(self) -> dict[str, Any]:
        rows = self.parse_all()
        return rows[0] if rows else {}

    @staticmethod
    def _find_value(row: dict[str, Any], headers: dict[str, str], column: str) -> Any:
        if column in row and row[column] is not None:
            return row[column]
        if column in headers:
            return row.get(headers[column])
        for alias in CSV_ALIASES.get(column, []):
            lower_alias = alias.strip().lower()
            if lower_alias in headers:
                return row.get(headers[lower_alias])
        # fallback to any matching case-insensitive header
        for header_key, original_header in headers.items():
            if header_key == column.lower():
                return row.get(original_header)
        return None

    @staticmethod
    def _clean_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
