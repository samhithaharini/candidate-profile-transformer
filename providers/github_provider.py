from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class GitHubProvider:
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate that the URL is a valid GitHub profile URL.
        Accepts format: https://github.com/<username>
        """
        # Regex matches https://github.com/ followed by non-empty alphanumeric/hyphen/underscore/percent/dot username, with optional trailing slash
        pattern = r"^https://github\.com/[a-zA-Z0-9\-_%.]+/?$"
        return bool(re.match(pattern, url))

    def __init__(self, sample_data_dir: Path | str = "sample_data") -> None:
        self.sample_data_dir = Path(sample_data_dir)

    def get_profile(self, url: str) -> dict[str, Any]:
        """
        Validate GitHub profile URL and load local sample data.
        """
        from providers import ValidationError

        if not self.validate_url(url):
            raise ValidationError(
                f"Invalid GitHub Profile URL: '{url}'. "
                "Expected format: https://github.com/<username>"
            )

        file_path = self.sample_data_dir / "github_profile.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Sample GitHub data file not found at: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
