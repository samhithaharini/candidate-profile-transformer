from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


@dataclass
class MatchResult:
    matched: bool
    score: float
    reason: str


class Matcher:
    def match(self, csv_record: dict[str, Any], resume_record: dict[str, Any]) -> MatchResult:
        # Check emails intersection
        if self._match_email(csv_record.get("emails"), resume_record.get("emails")):
            return MatchResult(True, 1.0, "email")
        
        # Check phones intersection
        if self._match_phone(csv_record.get("phones"), resume_record.get("phones")):
            return MatchResult(True, 0.9, "phone")
        
        # Check name similarity
        name_score = self._match_name(csv_record.get("full_name"), resume_record.get("full_name"))
        if name_score >= 0.85:
            # Check for hard conflicts in identifiers if they exist in both
            if self._has_identifier_conflict(csv_record, resume_record):
                return MatchResult(False, 0.0, "conflict_identifiers")

            # Company check heuristic to prevent matching ambiguous name duplicates
            if not self._check_company_overlap(csv_record, resume_record):
                return MatchResult(False, 0.0, "conflict_company")

            return MatchResult(True, round(name_score, 3), "name_similarity")
            
        return MatchResult(False, 0.0, "no_match")

    def _match_email(self, csv_emails: Any, resume_emails: Any) -> bool:
        if not isinstance(csv_emails, list) or not isinstance(resume_emails, list):
            return False
        set1 = {str(e).strip().lower() for e in csv_emails if e}
        set2 = {str(e).strip().lower() for e in resume_emails if e}
        return bool(set1 & set2)

    def _match_phone(self, csv_phones: Any, resume_phones: Any) -> bool:
        if not isinstance(csv_phones, list) or not isinstance(resume_phones, list):
            return False
        set1 = {str(p).strip().lower() for p in csv_phones if p}
        set2 = {str(p).strip().lower() for p in resume_phones if p}
        return bool(set1 & set2)

    def _match_name(self, csv_name: Any, resume_name: Any) -> float:
        if not csv_name or not resume_name:
            return 0.0
        normalized_csv = self._normalize_name(str(csv_name))
        normalized_resume = self._normalize_name(str(resume_name))
        if not normalized_csv or not normalized_resume:
            return 0.0
        return SequenceMatcher(None, normalized_csv, normalized_resume).ratio()

    def _normalize_name(self, name: str) -> str:
        """Make names robust to formatting differences across sources:
        accents/diacritics ("José" vs "Jose"), suffixes ("Jr.", "III"),
        and middle initials ("Jane A. Doe" vs "Jane Doe")."""
        import unicodedata
        stripped = unicodedata.normalize("NFKD", name)
        stripped = "".join(c for c in stripped if not unicodedata.combining(c))
        stripped = stripped.lower()
        stripped = re.sub(r"\b(jr|sr|ii|iii|iv)\.?\b", " ", stripped)
        stripped = re.sub(r"\b[a-z]\.\b", " ", stripped)  # middle initials like "a."

        # Keep Unicode letters and spaces, replacing other characters with spaces
        chars = []
        for c in stripped:
            if c.isspace() or unicodedata.category(c).startswith("L"):
                chars.append(c)
            else:
                chars.append(" ")
        stripped = "".join(chars)
        return re.sub(r"\s+", " ", stripped).strip()

    def _has_identifier_conflict(self, csv_record: dict[str, Any], resume_record: dict[str, Any]) -> bool:
        csv_emails = [str(e).strip().lower() for e in csv_record.get("emails") or [] if e]
        res_emails = [str(e).strip().lower() for e in resume_record.get("emails") or [] if e]
        if csv_emails and res_emails:
            # Both have emails, but zero overlap -> conflict!
            if not (set(csv_emails) & set(res_emails)):
                return True

        csv_phones = [str(p).strip().lower() for p in csv_record.get("phones") or [] if p]
        res_phones = [str(p).strip().lower() for p in resume_record.get("phones") or [] if p]
        if csv_phones and res_phones:
            # Both have phones, but zero overlap -> conflict!
            if not (set(csv_phones) & set(res_phones)):
                return True

        return False

    def _check_company_overlap(self, csv_record: dict[str, Any], resume_record: dict[str, Any]) -> bool:
        csv_companies = self._get_companies(csv_record)
        res_companies = self._get_companies(resume_record)

        # If either has no company info, we cannot check overlap, so we pass the match
        if not csv_companies or not res_companies:
            return True

        # Check if there is any overlap (direct substring or high similarity)
        for c1 in csv_companies:
            for c2 in res_companies:
                if c1 in c2 or c2 in c1 or SequenceMatcher(None, c1, c2).ratio() >= 0.8:
                    return True
        return False

    def _get_companies(self, record: dict[str, Any]) -> set[str]:
        companies = set()
        comp = record.get("metadata", {}).get("company")
        if comp:
            companies.add(str(comp).strip().lower())
        for exp in record.get("experience") or []:
            if isinstance(exp, dict) and exp.get("company"):
                companies.add(str(exp["company"]).strip().lower())
            elif isinstance(exp, str):
                match = re.split(r"\s+(?:at|@)\s+", exp, maxsplit=1, flags=re.IGNORECASE)
                if len(match) == 2:
                    companies.add(match[1].strip().lower())
        return {c for c in companies if c}
