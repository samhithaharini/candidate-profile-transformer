from __future__ import annotations

from pathlib import Path
from typing import Any

from parsers.csv_parser import CsvParser
from parsers.ats_json_parser import AtsJsonParser
from parsers.resume_parser import ResumeParser
from parsers.linkedin_json_parser import LinkedInJsonParser
from parsers.github_json_parser import GitHubJsonParser
from parsers.recruiter_notes_parser import RecruiterNotesParser


class ExtractionError(Exception):
    pass


class Extractor:
    def __init__(
        self,
        structured_path: Path,
        unstructured_path: Path,
        structured_type: str = "csv",
        unstructured_type: str = "pdf"
    ) -> None:
        self.structured_path = structured_path
        self.unstructured_path = unstructured_path
        self.structured_type = structured_type.lower()
        self.unstructured_type = unstructured_type.lower()

    def extract(self) -> dict[str, dict[str, Any]]:
        # Path validation
        if not self.structured_path:
            raise ExtractionError("Structured source file path is missing")
        if not self.unstructured_path:
            raise ExtractionError("Unstructured source file path is missing")

        if not self.structured_path.exists():
            raise ExtractionError(f"Structured file not found: {self.structured_path}")
        if not self.unstructured_path.exists():
            raise ExtractionError(f"Unstructured file not found: {self.unstructured_path}")

        # Extension validation
        struct_ext = self.structured_path.suffix.lower()
        unstruct_ext = self.unstructured_path.suffix.lower()

        if self.structured_type == "csv" and struct_ext != ".csv":
            raise ExtractionError(f"Wrong file extension for CSV source: expected .csv, got '{struct_ext}'")
        if self.structured_type in ("json", "ats_json") and struct_ext != ".json":
            raise ExtractionError(f"Wrong file extension for JSON source: expected .json, got '{struct_ext}'")

        if self.unstructured_type in ("pdf", "resume_pdf") and unstruct_ext != ".pdf":
            raise ExtractionError(f"Wrong file extension for PDF source: expected .pdf, got '{unstruct_ext}'")
        if self.unstructured_type in ("linkedin_json", "linkedin_profile", "github_json", "github_profile") and unstruct_ext != ".json":
            raise ExtractionError(f"Wrong file extension for JSON source: expected .json, got '{unstruct_ext}'")
        if self.unstructured_type in ("txt", "recruiter_notes") and unstruct_ext != ".txt":
            raise ExtractionError(f"Wrong file extension for TXT source: expected .txt, got '{unstruct_ext}'")

        # 1. Parse structured source
        try:
            if self.structured_type == "csv":
                structured_data = CsvParser(self.structured_path).parse()
            elif self.structured_type == "json" or self.structured_type == "ats_json":
                structured_data = AtsJsonParser(self.structured_path).parse()
            else:
                raise ExtractionError(f"Unsupported structured source type: {self.structured_type}")
        except Exception as error:
            raise ExtractionError(f"Structured extraction failed: {error}") from error

        # 2. Parse unstructured source
        try:
            if self.unstructured_type == "pdf" or self.unstructured_type == "resume_pdf":
                unstructured_data = ResumeParser(self.unstructured_path).parse()
            elif self.unstructured_type in ("linkedin_json", "linkedin_profile"):
                unstructured_data = LinkedInJsonParser(self.unstructured_path).parse()
            elif self.unstructured_type in ("github_json", "github_profile"):
                unstructured_data = GitHubJsonParser(self.unstructured_path).parse()
            elif self.unstructured_type == "txt" or self.unstructured_type == "recruiter_notes":
                unstructured_data = RecruiterNotesParser(self.unstructured_path).parse()
            else:
                raise ExtractionError(f"Unsupported unstructured source type: {self.unstructured_type}")
        except Exception as error:
            raise ExtractionError(f"Unstructured extraction failed: {error}") from error

        structured_canonical = self._canonicalize(structured_data, self.structured_type, is_structured=True)
        unstructured_canonical = self._canonicalize(unstructured_data, self.unstructured_type, is_structured=False)

        res = {
            "structured": structured_canonical,
            "unstructured": unstructured_canonical,
            # Backward compatibility aliases
            "csv": structured_canonical,
            "resume": unstructured_canonical,
        }
        return res

    def _canonicalize(self, data: dict[str, Any], source_type: str, is_structured: bool) -> dict[str, Any]:
        emails = data.get("emails") or []
        if not emails and data.get("email"):
            emails = [data["email"]]
        if isinstance(emails, str):
            emails = [emails]

        phones = data.get("phones") or []
        if not phones and data.get("phone"):
            phones = [data["phone"]]
        if isinstance(phones, str):
            phones = [phones]

        # Extract links
        links = data.get("links") or []
        if isinstance(links, str):
            links = [links]

        return {
            "candidate_id": data.get("candidate_id") or data.get("email") or (emails[0] if emails else None) or data.get("phone") or (phones[0] if phones else None) or data.get("name"),
            "full_name": data.get("name"),
            "emails": emails,
            "phones": phones,
            "location": data.get("location"),
            "links": links,
            "headline": data.get("headline") or data.get("title"),
            "years_experience": data.get("years_experience"),
            "skills": data.get("skills") or [],
            "experience": data.get("experience") or [],
            "education": data.get("education") or [],
            "field_confidence": {},
            "overall_confidence": None,
            "provenance": [],
            "metadata": {
                "source": source_type,
                "company": data.get("current_company"),
                "designation": data.get("title"),
                "is_structured": is_structured,
                "raw_text_present": bool(data.get("raw_text")),
            },
        }
