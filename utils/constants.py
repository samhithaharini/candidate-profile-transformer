from __future__ import annotations

from typing import Final

CSV_EXPECTED_COLUMNS: Final = [
    "name",
    "email",
    "phone",
    "current_company",
    "title",
    "location",
]
CSV_ALIASES: Final = {
    "company": ["current_company"],
    "designation": ["title"],
}
DEFAULT_REGION: Final = "US"
COUNTRY_ALIASES: Final = {
    "united states": "US",
    "us": "US",
    "usa": "US",
    "united states of america": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "canada": "CA",
    "germany": "DE",
    "deutschland": "DE",
    "france": "FR",
    "india": "IN",
    "australia": "AU",
    "china": "CN",
    "japan": "JP",
    "spain": "ES",
    "italy": "IT",
    "netherlands": "NL",
    "singapore": "SG",
}
SKILL_CANONICAL_MAP: Final = {
    "python": "Python",
    "py": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "data engineering": "Data Engineering",
    "data engineer": "Data Engineering",
    "data science": "Data Science",
    "software engineering": "Software Engineering",
    "software engineer": "Software Engineering",
    "project management": "Project Management",
    "devops": "DevOps",
    "cloud": "Cloud Computing",
    "aws": "Amazon Web Services",
    "azure": "Microsoft Azure",
}
