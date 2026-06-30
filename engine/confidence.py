from __future__ import annotations

import re
from typing import Any

SOURCE_RELIABILITY = {
    "resume": 1.0,
    "csv": 0.9,
}


class ConfidenceEngine:
    def score_field(self, field: str, csv_value: Any, resume_value: Any, merged_value: Any) -> float:
        """Deterministic field confidence formula.

        confidence = source_reliability * agreement_factor * validation_factor
        """
        csv_present = self._is_present(csv_value)
        resume_present = self._is_present(resume_value)
        
        source_reliability = self._source_reliability(csv_present, resume_present)
        agreement_factor = self._agreement(csv_value, resume_value)
        validation_factor = self._validate(field, merged_value)
        
        score = source_reliability * agreement_factor * validation_factor
        return round(score, 3)

    def score_fields(self, csv_record: dict[str, Any], resume_record: dict[str, Any], merged_record: dict[str, Any]) -> dict[str, float]:
        scores: dict[str, float] = {}
        fields = [
            "candidate_id",
            "full_name",
            "emails",
            "phones",
            "location",
            "links",
            "headline",
            "years_experience",
            "skills",
            "experience",
            "education",
        ]
        for field in fields:
            scores[field] = self.score_field(
                field,
                csv_record.get(field),
                resume_record.get(field),
                merged_record.get(field),
            )
        return scores

    def overall_confidence(self, field_scores: dict[str, float]) -> float:
        nonzero_scores = [score for score in field_scores.values() if score > 0.0]
        if not nonzero_scores:
            return 0.0
        return round(sum(nonzero_scores) / len(nonzero_scores), 3)

    def _is_present(self, val: Any) -> bool:
        if val in (None, "", [], {}):
            return False
        if isinstance(val, dict):
            return any(self._is_present(v) for v in val.values())
        if isinstance(val, list):
            return any(self._is_present(v) for v in val)
        return True

    def _source_reliability(self, csv_present: bool, resume_present: bool) -> float:
        if resume_present and csv_present:
            return (SOURCE_RELIABILITY["resume"] + SOURCE_RELIABILITY["csv"]) / 2
        if resume_present:
            return SOURCE_RELIABILITY["resume"]
        if csv_present:
            return SOURCE_RELIABILITY["csv"]
        return 0.0

    def _agreement(self, csv_value: Any, resume_value: Any) -> float:
        if not self._is_present(csv_value) or not self._is_present(resume_value):
            return 1.0
        return 1.0 if csv_value == resume_value else 0.8

    def _validate(self, field: str, value: Any) -> float:
        if not self._is_present(value):
            return 0.0
        if field == "emails":
            return 1.0 if self._validate_emails(value) else 0.7
        if field == "phones":
            return 1.0 if self._validate_phones(value) else 0.7
        if field == "location":
            # validate country is 2-letter ISO
            if isinstance(value, dict):
                country = value.get("country")
                if country and len(str(country)) == 2:
                    return 1.0
            return 0.8
        return 1.0

    def _validate_emails(self, emails: Any) -> bool:
        if not isinstance(emails, list):
            return False
        for email in emails:
            if not isinstance(email, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                return False
        return bool(emails)

    def _validate_phones(self, phones: Any) -> bool:
        if not isinstance(phones, list):
            return False
        for phone in phones:
            if not isinstance(phone, str) or not re.match(r"^\+[1-9][0-9]{1,14}$", phone):
                return False
        return bool(phones)
