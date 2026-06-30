from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import phonenumbers

from utils.constants import COUNTRY_ALIASES, SKILL_CANONICAL_MAP, DEFAULT_REGION


class NormalizationError(Exception):
    pass


class Normalizer:
    def normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        source = record.get("metadata", {}).get("source", "unknown")

        for key, value in record.items():
            if key == "phone":
                normalized[key] = self._normalize_phone(value)
            elif key == "emails":
                normalized[key] = self._normalize_email_list(value)
            elif key == "phones":
                normalized[key] = self._normalize_phone_list(value)
            elif key == "email":
                normalized[key] = self._normalize_email(value)
            elif key == "location":
                normalized[key] = self._normalize_location(value)
            elif key == "links":
                normalized[key] = self._normalize_links(value)
            elif key == "skills":
                normalized[key] = self._normalize_skills(value, source)
            elif key == "experience":
                normalized[key] = self._normalize_experience(value)
            elif key == "education":
                normalized[key] = self._normalize_education(value)
            elif key == "years_experience":
                normalized[key] = self._normalize_years_experience(value)
            elif key == "raw_text":
                normalized[key] = value
            else:
                normalized[key] = value
        return normalized

    def _normalize_phone_list(self, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            normalized_phone = self._normalize_phone(value)
            return [normalized_phone] if normalized_phone else []
        if isinstance(value, list):
            normalized_values = [self._normalize_phone(item) for item in value]
            return [item for item in normalized_values if item]
        return []

    def _normalize_email_list(self, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            email = self._normalize_email(value)
            return [email] if email else []
        if isinstance(value, list):
            normalized_values = [self._normalize_email(item) for item in value]
            return [item for item in normalized_values if item]
        return []

    def _normalize_list(self, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        
        res = []
        for item in value:
            if not item:
                continue
            if isinstance(item, dict):
                # Shape mismatch guard: caller asked for flat strings but item is a
                # structured object (e.g. a skill {"name": ..., "confidence": ...}).
                # Pull out a sensible scalar instead of stringifying the whole dict.
                item = item.get("name") or item.get("value")
                if not item:
                    continue
            item_str = str(item).strip()
            canonical = SKILL_CANONICAL_MAP.get(item_str.lower(), item_str)
            res.append(canonical)
        return res

    def _normalize_phone(self, value: Any) -> str | None:
        if not value:
            return None
        val_str = str(value).strip()
        try:
            parsed = phonenumbers.parse(val_str, DEFAULT_REGION)
            if phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            pass

        # Fallback to cleaning non-alphanumeric except + and x (for extensions)
        try:
            cleaned = re.sub(r"[^0-9+x]+", "", val_str.lower())
            parsed = phonenumbers.parse(cleaned, DEFAULT_REGION)
            if phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            pass
        return None

    def _normalize_email(self, value: Any) -> str | None:
        if not value:
            return None
        email = str(value).strip().lower()
        return email if email else None

    def _normalize_country(self, value: Any) -> str | None:
        if not value:
            return None
        country = str(value).strip().lower()
        if not country:
            return None
        iso = COUNTRY_ALIASES.get(country)
        if iso:
            return iso
        if len(country) == 2:
            return country.upper()
        return country.title()

    def _normalize_location(self, value: Any) -> dict[str, str | None]:
        res: dict[str, str | None] = {"city": None, "region": None, "country": None}
        if not value:
            return res

        if isinstance(value, dict):
            res["city"] = value.get("city") or value.get("town")
            res["region"] = value.get("region") or value.get("state") or value.get("province")
            res["country"] = self._normalize_country(value.get("country"))
            return res

        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            if len(parts) == 3:
                res["city"] = parts[0]
                res["region"] = parts[1]
                res["country"] = self._normalize_country(parts[2])
            elif len(parts) == 2:
                # Could be city + region, or city/region + country
                first, second = parts[0], parts[1]
                norm_country = self._normalize_country(second)
                if norm_country and len(norm_country) == 2 and norm_country.isupper():
                    res["city"] = first
                    res["country"] = norm_country
                else:
                    res["city"] = first
                    res["region"] = second
            elif len(parts) == 1:
                norm_country = self._normalize_country(parts[0])
                if norm_country and (len(norm_country) == 2 or norm_country.lower() in COUNTRY_ALIASES):
                    res["country"] = norm_country
                else:
                    res["city"] = parts[0]
        return res

    def _normalize_links(self, value: Any) -> dict[str, Any]:
        res: dict[str, Any] = {"linkedin": None, "github": None, "portfolio": None, "other": []}
        if not value:
            return res

        urls = []
        if isinstance(value, dict):
            res["linkedin"] = value.get("linkedin")
            res["github"] = value.get("github")
            res["portfolio"] = value.get("portfolio")
            other_urls = value.get("other") or []
            res["other"] = other_urls if isinstance(other_urls, list) else [other_urls]
            return res

        if isinstance(value, list):
            urls = [str(u).strip() for u in value if u]
        elif isinstance(value, str):
            urls = [item.strip() for item in re.split(r"[\s,;]+", value) if item.strip()]

        for url in urls:
            url_lower = url.lower()
            if "linkedin.com" in url_lower:
                res["linkedin"] = url
            elif "github.com" in url_lower:
                res["github"] = url
            elif not res["portfolio"]:
                res["portfolio"] = url
            elif url not in res["other"]:
                res["other"].append(url)
        return res

    def _normalize_skills(self, value: Any, source: str) -> list[dict[str, Any]]:
        raw_items: list[Any] = []
        if isinstance(value, str):
            raw_items = [item.strip() for item in re.split(r"[\n,;•]+", value) if item.strip()]
        elif isinstance(value, list):
            raw_items = value
        else:
            return []

        skills: list[dict[str, Any]] = []
        seen_names = set()

        for item in raw_items:
            if not item:
                continue
            if isinstance(item, str):
                name = item.strip()
                confidence = 1.0
                sources = [source] if source else []
            elif isinstance(item, dict):
                name = item.get("name") or ""
                confidence = item.get("confidence", 1.0)
                sources = item.get("sources") or ([source] if source else [])
                if isinstance(sources, str):
                    sources = [sources]
            else:
                continue

            if not name:
                continue

            canonical_name = SKILL_CANONICAL_MAP.get(name.lower(), name)
            canonical_lower = canonical_name.lower()
            if canonical_lower not in seen_names:
                seen_names.add(canonical_lower)
                skills.append({
                    "name": canonical_name,
                    "confidence": float(confidence),
                    "sources": list(sources)
                })
        return skills

    def _normalize_experience(self, value: Any) -> list[dict[str, Any]]:
        raw_items = []
        if isinstance(value, str):
            raw_items = [item.strip() for item in re.split(r"[\n;•]+", value) if item.strip()]
        elif isinstance(value, list):
            raw_items = value
        else:
            return []

        experience = []
        for item in raw_items:
            if not item:
                continue
            if isinstance(item, str):
                # parse "Title at Company"
                title, company = None, None
                match = re.split(r"\s+(?:at|@)\s+", item, maxsplit=1, flags=re.IGNORECASE)
                if len(match) == 2:
                    title, company = match[0].strip(), match[1].strip()
                else:
                    title = item.strip()
                experience.append({
                    "company": company,
                    "title": title,
                    "start": None,
                    "end": None,
                    "summary": item.strip()
                })
            elif isinstance(item, dict):
                experience.append({
                    "company": item.get("company"),
                    "title": item.get("title"),
                    "start": self.normalize_dates(item.get("start")),
                    "end": self.normalize_dates(item.get("end")),
                    "summary": item.get("summary")
                })
        return experience

    def _normalize_education(self, value: Any) -> list[dict[str, Any]]:
        raw_items = []
        if isinstance(value, str):
            raw_items = [item.strip() for item in re.split(r"[\n;•]+", value) if item.strip()]
        elif isinstance(value, list):
            raw_items = value
        else:
            return []

        education = []
        for item in raw_items:
            if not item:
                continue
            if isinstance(item, str):
                education.append({
                    "institution": None,
                    "degree": item.strip(),
                    "field": None,
                    "end_year": None
                })
            elif isinstance(item, dict):
                end_year = item.get("end_year")
                if isinstance(end_year, str):
                    try:
                        end_year = int(end_year)
                    except ValueError:
                        end_year = None
                education.append({
                    "institution": item.get("institution") or item.get("school"),
                    "degree": item.get("degree"),
                    "field": item.get("field"),
                    "end_year": end_year
                })
        return education

    def _normalize_years_experience(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def normalize_dates(self, value: Any) -> Any:
        if not value:
            return None
        val_str = re.sub(r"\s+", " ", str(value).replace(",", " ")).strip()
        if val_str.lower() in ("present", "now", "current", "currently working", "currently"):
            return "Present"
        # Try various date formats
        formats = [
            "%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m", "%m/%Y",
            "%B %Y", "%b %Y", "%Y",
            "%b %y", "%B %y", "%m/%y"
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(val_str, fmt)
                if fmt == "%Y":
                    return parsed.strftime("%Y-01")
                return parsed.strftime("%Y-%m")
            except ValueError:
                continue
        # regex search for YYYY-MM
        match = re.search(r"\b(\d{4})[-/](\d{1,2})\b", val_str)
        if match:
            year, month = match.group(1), match.group(2).zfill(2)
            return f"{year}-{month}"
        match_yr = re.search(r"\b(\d{4})\b", val_str)
        if match_yr:
            return f"{match_yr.group(1)}-01"
        return val_str
