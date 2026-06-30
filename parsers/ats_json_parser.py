from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AtsJsonParserError(Exception):
    pass


class AtsJsonParser:
    def __init__(self, path: Path) -> None:
        self.path = path

    def parse(self) -> dict[str, Any]:
        from utils.file_utils import read_text_robust

        if not self.path.exists():
            raise AtsJsonParserError(f"ATS JSON file not found: {self.path}")
        try:
            content = read_text_robust(self.path)
            if not content or not content.strip():
                raise AtsJsonParserError("ATS JSON file is empty")
            data = json.loads(content)
        except Exception as error:
            raise AtsJsonParserError(f"Failed to parse ATS JSON: {error}") from error

        if isinstance(data, list):
            if not data:
                raise AtsJsonParserError("ATS JSON is an empty list")
            record = data[0]
        elif isinstance(data, dict):
            record = data
        else:
            raise AtsJsonParserError("ATS JSON root must be a list or dictionary")

        return self._extract_fields(record)

    def _scalarize(self, value: Any) -> Any:
        """Defend against ATS fields that don't map cleanly to our schema: a field we
        expect as a scalar string sometimes arrives as a list or a nested object.
        Pull out a sensible scalar instead of letting it get silently stringified
        downstream (e.g. str({'mobile': '...'}) leaking into the output)."""
        if isinstance(value, list):
            for item in value:
                scal = self._scalarize(item)
                if scal:
                    return scal
            return None
        if isinstance(value, dict):
            for key in ("value", "primary", "address", "number", "mobile", "email", "phone"):
                scal = self._scalarize(value.get(key))
                if scal:
                    return scal
            for v in value.values():
                scal = self._scalarize(v)
                if scal:
                    return scal
            return None
        if value is not None:
            return str(value).strip() or None
        return None

    def _extract_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        # Extract full name
        name = record.get("name") or record.get("full_name") or record.get("candidate_name")
        if not name and "first_name" in record:
            name = f"{record.get('first_name', '')} {record.get('last_name', '')}".strip()
        name = self._scalarize(name)

        # Extract email
        email = record.get("email") or record.get("email_address")
        if not email and isinstance(record.get("emails"), list) and record["emails"]:
            email = record["emails"][0]
        email = self._scalarize(email)

        # Extract phone
        phone = record.get("phone") or record.get("phone_number") or record.get("mobile")
        if not phone and isinstance(record.get("phones"), list) and record["phones"]:
            phone = record["phones"][0]
        phone = self._scalarize(phone)

        # Extract company & title
        company = self._scalarize(record.get("current_company") or record.get("company") or record.get("employer"))
        title = self._scalarize(
            record.get("title") or record.get("headline") or record.get("role") or record.get("designation")
        )

        # Additional rich fields
        skills = record.get("skills") or record.get("technical_skills") or []
        experience = record.get("experience") or record.get("work_history") or []
        education = record.get("education") or record.get("qualifications") or []
        location = record.get("location") or record.get("address")
        links = record.get("links") or record.get("urls") or []

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "current_company": company,
            "title": title,
            "skills": skills if isinstance(skills, list) else [skills],
            "experience": experience if isinstance(experience, list) else [experience],
            "education": education if isinstance(education, list) else [education],
            "location": location,
            "links": links if isinstance(links, list) else [links],
        }
