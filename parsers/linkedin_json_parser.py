from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LinkedInJsonParserError(Exception):
    pass


class LinkedInJsonParser:
    def __init__(self, path: Path) -> None:
        self.path = path

    def parse(self) -> dict[str, Any]:
        from utils.file_utils import read_text_robust

        if not self.path.exists():
            raise LinkedInJsonParserError(f"LinkedIn JSON file not found: {self.path}")
        try:
            content = read_text_robust(self.path)
            if not content or not content.strip():
                raise LinkedInJsonParserError("LinkedIn JSON file is empty")
            data = json.loads(content)
        except Exception as error:
            raise LinkedInJsonParserError(f"Failed to parse LinkedIn JSON: {error}") from error

        if isinstance(data, list):
            if not data:
                raise LinkedInJsonParserError("LinkedIn JSON is empty")
            record = data[0]
        elif isinstance(data, dict):
            record = data
        else:
            raise LinkedInJsonParserError("LinkedIn JSON must be a dictionary or list")

        return self._extract_fields(record)

    def _extract_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        name = record.get("name") or record.get("full_name") or record.get("formatted_name")
        email = record.get("email") or record.get("email_address")
        phone = record.get("phone") or record.get("phone_number")
        headline = record.get("headline") or record.get("title")

        # Location could be string or object
        location = record.get("location")

        # Skills - list of strings or list of dicts
        raw_skills = record.get("skills") or []
        skills = []
        for skill in raw_skills:
            if isinstance(skill, str):
                skills.append(skill)
            elif isinstance(skill, dict) and "name" in skill:
                skills.append(skill["name"])

        # Experience
        raw_exp = record.get("positions") or record.get("experience") or []
        experience = []
        for item in raw_exp:
            if isinstance(item, str):
                experience.append(item)
            elif isinstance(item, dict):
                # Extract structured position details
                company = item.get("company_name") or item.get("company")
                title = item.get("title")
                start = item.get("start_date") or item.get("start")
                end = item.get("end_date") or item.get("end") or "Present"
                desc = item.get("description") or item.get("summary") or ""
                experience.append({
                    "company": company,
                    "title": title,
                    "start": start,
                    "end": end,
                    "summary": desc
                })

        # Education
        raw_edu = record.get("educations") or record.get("education") or []
        education = []
        for item in raw_edu:
            if isinstance(item, str):
                education.append(item)
            elif isinstance(item, dict):
                school = item.get("school_name") or item.get("school") or item.get("institution")
                degree = item.get("degree")
                field = item.get("field_of_study") or item.get("field")
                end_year_val = item.get("end_date") or item.get("end_year") or item.get("end")
                
                # Extract year
                end_year = None
                if end_year_val:
                    try:
                        if isinstance(end_year_val, int):
                            end_year = end_year_val
                        elif isinstance(end_year_val, str):
                            # Try to extract 4 digit year
                            match = re.search(r"\b\d{4}\b", end_year_val)
                            if match:
                                end_year = int(match.group(0))
                    except Exception:
                        pass
                education.append({
                    "institution": school,
                    "degree": degree,
                    "field": field,
                    "end_year": end_year
                })

        # Links
        links = []
        linkedin_url = record.get("linkedin_url") or record.get("url")
        if linkedin_url:
            links.append(linkedin_url)
        websites = record.get("websites") or record.get("links") or []
        if isinstance(websites, list):
            for site in websites:
                if isinstance(site, str):
                    links.append(site)
                elif isinstance(site, dict) and "url" in site:
                    links.append(site["url"])
        elif isinstance(websites, str):
            links.append(websites)

        return {
            "raw_text": json.dumps(record, indent=2),
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "education": education,
            "experience": experience,
            "links": links,
            "location": location,
            "headline": headline,
        }


import re
