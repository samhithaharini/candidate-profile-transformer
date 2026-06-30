from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class LinkedInProvider:
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate that the URL is a valid LinkedIn profile URL.
        Accepts format: https://www.linkedin.com/in/<profile-slug>
        """
        # Regex matches https://www.linkedin.com/in/ followed by non-empty alphanumeric/hyphen/underscore/percent/dot slug, with optional trailing slash
        pattern = r"^https://www\.linkedin\.com/in/[a-zA-Z0-9\-_%.]+/?$"
        return bool(re.match(pattern, url))

    def __init__(self, sample_data_dir: Path | str = "sample_data") -> None:
        self.sample_data_dir = Path(sample_data_dir)

    def get_profile(self, url: str) -> dict[str, Any]:
        """
        Validate LinkedIn profile URL and load local sample data.
        """
        from providers import ValidationError

        if not self.validate_url(url):
            raise ValidationError(
                f"Invalid LinkedIn Profile URL: '{url}'. "
                "Expected format: https://www.linkedin.com/in/<profile-slug>"
            )

        file_path = self.sample_data_dir / "linkedin_profile.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Sample LinkedIn data file not found at: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
