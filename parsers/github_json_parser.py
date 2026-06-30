from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GitHubJsonParserError(Exception):
    pass


class GitHubJsonParser:
    def __init__(self, path: Path) -> None:
        self.path = path

    def parse(self) -> dict[str, Any]:
        from utils.file_utils import read_text_robust

        if not self.path.exists():
            raise GitHubJsonParserError(f"GitHub JSON file not found: {self.path}")
        try:
            content = read_text_robust(self.path)
            if not content or not content.strip():
                raise GitHubJsonParserError("GitHub JSON file is empty")
            data = json.loads(content)
        except Exception as error:
            raise GitHubJsonParserError(f"Failed to parse GitHub JSON: {error}") from error

        if isinstance(data, list):
            if not data:
                raise GitHubJsonParserError("GitHub JSON is empty")
            record = data[0]
        elif isinstance(data, dict):
            record = data
        else:
            raise GitHubJsonParserError("GitHub JSON must be a dictionary or list")

        return self._extract_fields(record)

    def _extract_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        name = record.get("name") or record.get("login")
        email = record.get("email")
        bio = record.get("bio")
        location = record.get("location")

        # Links
        links = []
        github_url = record.get("html_url") or record.get("url")
        if github_url:
            links.append(github_url)
        blog = record.get("blog")
        if blog:
            links.append(blog)

        # Extracted skills (languages from repositories list)
        skills_set = set()
        experience = []

        repos = record.get("repositories") or record.get("repos") or []
        if isinstance(repos, list):
            for repo in repos:
                if isinstance(repo, dict):
                    lang = repo.get("language")
                    if lang:
                        skills_set.add(lang)
                    repo_name = repo.get("name")
                    repo_desc = repo.get("description") or ""
                    if repo_name:
                        summary = f"GitHub repository {repo_name}"
                        if repo_desc:
                            summary += f": {repo_desc}"
                        if lang:
                            summary += f" ({lang})"
                        experience.append({
                            "company": "GitHub Open Source",
                            "title": "Contributor / Author",
                            "start": None,
                            "end": None,
                            "summary": summary
                        })
        elif isinstance(repos, dict):
            # languages frequency map
            for lang in repos.keys():
                skills_set.add(lang)

        # If language is mentioned in bio, we can add it
        if bio:
            for skill_word in ["python", "javascript", "typescript", "java", "golang", "rust", "c++", "ruby"]:
                if f" {skill_word} " in f" {bio.lower()} ":
                    skills_set.add(skill_word.capitalize())

        return {
            "raw_text": json.dumps(record, indent=2),
            "name": name,
            "email": email,
            "phone": None,
            "skills": list(skills_set),
            "education": [],
            "experience": experience,
            "links": links,
            "location": location,
            "headline": bio,
        }
