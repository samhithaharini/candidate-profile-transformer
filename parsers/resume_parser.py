from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+\s*@\s*[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"\+?[0-9][0-9\-(). ]{6,}[0-9]")
LINK_PATTERN = re.compile(
    r"(?:https?://|www\.)[a-zA-Z0-9\-_.]+\.[a-zA-Z]{2,}\b(?:/[^\s|]*)?|[a-zA-Z0-9\-_.]+\.(?:com|org|net|io|edu|co|in|dev)\b(?:/[^\s|]*)?",
    re.IGNORECASE,
)
LOCATION_HINTS = ["Location", "Address", "City", "State", "Country"]
HEADLINE_HINTS = ["Summary", "Objective", "Professional Summary", "About"]
SECTION_HEADERS = [
    "Skills", "Technical Skills", "Competencies", "Key Skills", "Keywords",
    "Education", "Academic", "Qualifications", "Degrees",
    "Experience", "Professional Experience", "Work Experience", "History", "Employment", "Internship Experience", "Internship",
    "Projects", "Certifications", "Publications", "Awards",
    *LOCATION_HINTS, *HEADLINE_HINTS,
]


class ResumeParserError(Exception):
    pass


class ResumeParser:
    def __init__(self, path: Path) -> None:
        self.path = path

    def parse(self) -> dict[str, Any]:
        if not self.path.exists():
            raise ResumeParserError(f"Resume file not found: {self.path}")
        try:
            with pdfplumber.open(self.path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as error:
            raise ResumeParserError(f"Unable to parse PDF: {error}") from error
        if not text or not text.strip():
            raise ResumeParserError(f"Resume PDF contains no text: {self.path}")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        joined = "\n".join(lines)
        return {
            "raw_text": joined,
            "name": self._extract_name(lines),
            "email": self._extract_first(EMAIL_PATTERN, joined),
            "phone": self._extract_first(PHONE_PATTERN, joined),
            "skills": self._extract_section(joined, ["Skills", "Technical Skills", "Competencies", "Key Skills", "Keywords"]),
            "education": self._extract_section(joined, ["Education", "Academic", "Qualifications", "Degrees"]),
            "experience": self._extract_section(joined, ["Experience", "Professional Experience", "Work Experience", "History", "Employment", "Internship Experience", "Internship"]),
            "links": self._extract_all(LINK_PATTERN, joined),
            "location": self._extract_section_value(joined, LOCATION_HINTS),
            "headline": self._extract_section_value(joined, HEADLINE_HINTS),
        }

    def _extract_first(self, pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        if not match:
            return None
        val = match.group(0).strip()
        if "@" in val:
            val = val.replace(" ", "")
        return val

    def _extract_all(self, pattern: re.Pattern[str], text: str) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        for match in pattern.finditer(text):
            value = match.group(0).strip()
            if "@" in value:
                continue
            # Ignore if preceded by '@' (ignoring whitespace)
            start = match.start()
            preceding = text[max(0, start-5):start]
            if "@" in preceding:
                continue
            # Ignore generic email domain names
            if value.lower() in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com"):
                continue
            if value and value not in seen:
                seen.add(value)
                values.append(value)
        return values

    def _extract_name(self, lines: list[str]) -> str | None:
        if not lines:
            return None
        first_line = lines[0]
        if "@" not in first_line and not any(char.isdigit() for char in first_line):
            return first_line
        for line in lines[:5]:
            if "@" not in line and not any(char.isdigit() for char in line):
                return line
        return None

    def _extract_section(self, text: str, headers: list[str]) -> list[str]:
        other_headers = [h for h in SECTION_HEADERS if h.lower() not in (hh.lower() for hh in headers)]
        boundary = "|".join(re.escape(h) for h in other_headers)
        for header in headers:
            pattern = re.compile(
                rf"(?:^|\n)\s*[-•*]?\s*{re.escape(header)}\s*[:\-]?\s*\n?(.+?)(?=\n\s*(?:{boundary})\s*[:\-]?\s*\n|\n\s*\w+:|\n\n|\Z)",
                re.IGNORECASE | re.DOTALL,
            )
            match = pattern.search(text)
            if match:
                section_text = match.group(1)
                return self._split_list(section_text)
        return []

    def _extract_section_value(self, text: str, headers: list[str]) -> str | None:
        for header in headers:
            pattern = re.compile(rf"{re.escape(header)}\s*[:\-]?\s*(.+)", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None

    def _split_list(self, value: str) -> list[str]:
        items = [item.strip() for item in re.split(r"[\n,;•]+", value) if item.strip()]
        return items
