from __future__ import annotations

from typing import Any


class Merger:
    def merge(self, csv_record: dict[str, Any], resume_record: dict[str, Any]) -> dict[str, Any]:
        merged, _ = self.merge_with_reasons(csv_record, resume_record)
        return merged

    def merge_with_reasons(self, csv_record: dict[str, Any], resume_record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        merged: dict[str, Any] = {}
        merge_reasons: dict[str, str] = {}
        
        # Merge basic fields
        simple_fields = ["candidate_id", "full_name", "headline", "years_experience"]
        for field in simple_fields:
            csv_val = csv_record.get(field)
            res_val = resume_record.get(field)
            merged[field], merge_reasons[field] = self._resolve_simple_value(csv_val, res_val)

        # Merge list fields
        list_fields = ["emails", "phones"]
        for field in list_fields:
            csv_val = csv_record.get(field) or []
            res_val = resume_record.get(field) or []
            merged[field], merge_reasons[field] = self._resolve_list_value(csv_val, res_val)

        # Merge complex fields
        merged["location"], merge_reasons["location"] = self._merge_location(
            csv_record.get("location"), resume_record.get("location")
        )
        merged["links"], merge_reasons["links"] = self._merge_links(
            csv_record.get("links"), resume_record.get("links")
        )
        merged["skills"], merge_reasons["skills"] = self._merge_skills(
            csv_record.get("skills") or [], resume_record.get("skills") or []
        )
        merged["experience"], merge_reasons["experience"] = self._merge_experience(
            csv_record.get("experience") or [], resume_record.get("experience") or []
        )
        merged["education"], merge_reasons["education"] = self._merge_education(
            csv_record.get("education") or [], resume_record.get("education") or []
        )

        return merged, merge_reasons

    def _resolve_simple_value(self, csv_value: Any, resume_value: Any) -> tuple[Any, str]:
        if resume_value not in (None, "", [], {}):
            if csv_value not in (None, "", [], {}) and csv_value != resume_value:
                return resume_value, "resume_priority"
            return resume_value, "resume_value"
        if csv_value not in (None, "", [], {}):
            return csv_value, "csv_value"
        return None, "missing"

    def _resolve_list_value(self, csv_list: list[Any], resume_list: list[Any]) -> tuple[list[Any], str]:
        if not csv_list and not resume_list:
            return [], "missing"
        
        merged = []
        # Union elements while keeping order, prefer resume order first
        seen = set()
        for item in resume_list:
            if item and item not in seen:
                seen.add(item)
                merged.append(item)
        for item in csv_list:
            if item and item not in seen:
                seen.add(item)
                merged.append(item)

        if csv_list and resume_list:
            return merged, "merged_arrays"
        elif resume_list:
            return merged, "resume_value"
        return merged, "csv_value"

    def _merge_location(self, csv_loc: Any, res_loc: Any) -> tuple[dict[str, str | None], str]:
        default_loc = {"city": None, "region": None, "country": None}
        csv_l = csv_loc if isinstance(csv_loc, dict) else default_loc
        res_l = res_loc if isinstance(res_loc, dict) else default_loc

        merged = {}
        has_csv = any(csv_l.values())
        has_res = any(res_l.values())

        for key in ["city", "region", "country"]:
            c_val = csv_l.get(key)
            r_val = res_l.get(key)
            merged[key] = r_val or c_val

        if has_csv and has_res:
            return merged, "merged_location"
        elif has_res:
            return merged, "resume_location"
        elif has_csv:
            return merged, "csv_location"
        return merged, "missing"

    def _merge_links(self, csv_links: Any, res_links: Any) -> tuple[dict[str, Any], str]:
        default_links = {"linkedin": None, "github": None, "portfolio": None, "other": []}
        csv_l = csv_links if isinstance(csv_links, dict) else default_links
        res_l = res_links if isinstance(res_links, dict) else default_links

        merged = {}
        merged["linkedin"] = res_l.get("linkedin") or csv_l.get("linkedin")
        merged["github"] = res_l.get("github") or csv_l.get("github")
        merged["portfolio"] = res_l.get("portfolio") or csv_l.get("portfolio")
        
        # Merge other list
        others = []
        seen = set()
        for u in (res_l.get("other") or []):
            if u not in seen:
                seen.add(u)
                others.append(u)
        for u in (csv_l.get("other") or []):
            if u not in seen:
                seen.add(u)
                others.append(u)
        merged["other"] = others

        has_csv = any(v for k, v in csv_l.items() if k != "other") or csv_l.get("other")
        has_res = any(v for k, v in res_l.items() if k != "other") or res_l.get("other")

        if has_csv and has_res:
            return merged, "merged_links"
        elif has_res:
            return merged, "resume_links"
        return merged, "csv_links"

    def _merge_skills(self, csv_skills: list[dict[str, Any]], res_skills: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        merged_skills: list[dict[str, Any]] = []
        skills_map: dict[str, dict[str, Any]] = {}

        # Put resume skills first
        for s in res_skills:
            name_lower = s["name"].lower()
            skills_map[name_lower] = {
                "name": s["name"],
                "confidence": s["confidence"],
                "sources": list(s["sources"])
            }

        # Merge csv skills
        for s in csv_skills:
            name_lower = s["name"].lower()
            if name_lower in skills_map:
                # Merge sources and update confidence
                existing = skills_map[name_lower]
                for src in s["sources"]:
                    if src not in existing["sources"]:
                        existing["sources"].append(src)
                existing["confidence"] = max(existing["confidence"], s["confidence"])
            else:
                skills_map[name_lower] = {
                    "name": s["name"],
                    "confidence": s["confidence"],
                    "sources": list(s["sources"])
                }

        merged_skills = list(skills_map.values())
        if csv_skills and res_skills:
            return merged_skills, "merged_skills"
        elif res_skills:
            return merged_skills, "resume_skills"
        return merged_skills, "csv_skills"

    def _merge_experience(self, csv_exp: list[dict[str, Any]], res_exp: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        # Simple deduplicated combination based on company & title match
        merged = []
        seen = set()

        for item in res_exp:
            key = (str(item.get("company") or "").lower(), str(item.get("title") or "").lower())
            seen.add(key)
            merged.append(item)

        for item in csv_exp:
            key = (str(item.get("company") or "").lower(), str(item.get("title") or "").lower())
            if key not in seen:
                seen.add(key)
                merged.append(item)

        if csv_exp and res_exp:
            return merged, "merged_experience"
        elif res_exp:
            return merged, "resume_experience"
        return merged, "csv_experience"

    def _merge_education(self, csv_edu: list[dict[str, Any]], res_edu: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        merged = []
        seen = set()

        for item in res_edu:
            key = (str(item.get("institution") or "").lower(), str(item.get("degree") or "").lower())
            seen.add(key)
            merged.append(item)

        for item in csv_edu:
            key = (str(item.get("institution") or "").lower(), str(item.get("degree") or "").lower())
            if key not in seen:
                seen.add(key)
                merged.append(item)

        if csv_edu and res_edu:
            return merged, "merged_education"
        elif res_edu:
            return merged, "resume_education"
        return merged, "csv_education"
