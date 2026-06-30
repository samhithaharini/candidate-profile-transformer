from __future__ import annotations

from typing import Any


class ProvenanceEngine:
    def build_provenance(
        self,
        merged: dict[str, Any],
        merge_reasons: dict[str, str],
        csv_record: dict[str, Any],
        resume_record: dict[str, Any]
    ) -> list[dict[str, Any]]:
        provenance: list[dict[str, Any]] = []
        
        csv_source = csv_record.get("metadata", {}).get("source", "csv")
        resume_source = resume_record.get("metadata", {}).get("source", "resume")

        for field, value in merged.items():
            if field in {"provenance", "field_confidence", "overall_confidence", "metadata"}:
                continue
                
            if not self._is_present(value):
                provenance.append({
                    "field": field,
                    "source": "none",
                    "method": "not_found",
                    "selected_value": None,
                })
                continue

            reason = merge_reasons.get(field, "")
            
            # Determine source based on reason prefix or exact string
            if "resume" in reason or reason == "resume_priority":
                source = resume_source
                method = "priority_rule"
            elif "csv" in reason:
                source = csv_source
                method = "priority_rule"
            elif "merged" in reason:
                source = f"merged({csv_source}+{resume_source})"
                method = "union"
            else:
                # Fallback check
                resume_present = self._is_present(resume_record.get(field))
                csv_present = self._is_present(csv_record.get(field))
                if resume_present and csv_present:
                    source = f"merged({csv_source}+{resume_source})"
                    method = "union" if isinstance(value, list) else "priority_rule"
                elif resume_present:
                    source = resume_source
                    method = "priority_rule"
                elif csv_present:
                    source = csv_source
                    method = "priority_rule"
                else:
                    source = "unknown"
                    method = "fallback"

            provenance.append({
                "field": field,
                "source": source,
                "method": method,
                "selected_value": value,
            })
        return provenance

    def _is_present(self, val: Any) -> bool:
        if val in (None, "", [], {}):
            return False
        if isinstance(val, dict):
            return any(self._is_present(v) for v in val.values())
        if isinstance(val, list):
            return any(self._is_present(v) for v in val)
        return True
