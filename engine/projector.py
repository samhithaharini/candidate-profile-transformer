from __future__ import annotations

import re
from typing import Any
from engine.normalizer import Normalizer


class Projector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.fields = config.get("fields", [])
        self.include_confidence = config.get("include_confidence", config.get("enable_confidence", True))
        self.include_provenance = config.get("include_provenance", config.get("enable_provenance", True))
        self.include_metadata = config.get("include_metadata", config.get("enable_metadata", True))
        self.on_missing = config.get("on_missing", config.get("missing_field_policy", "omit"))

        # Fallback fields for old configuration style
        self.selected_fields = config.get("selected_fields", [])
        self.field_renames = config.get("field_renames", config.get("renamed_fields", {}))

        self._validate_config()

    def _validate_config(self) -> None:
        """Fail fast on a self-conflicting config instead of silently dropping data."""
        if self.fields:
            seen_paths: dict[str, str] = {}
            for field_cfg in self.fields:
                path = field_cfg.get("path")
                if not path:
                    continue
                from_expr = field_cfg.get("from") or path
                if path in seen_paths and seen_paths[path] != from_expr:
                    raise ValueError(
                        f"Invalid config: output path '{path}' is targeted by multiple fields "
                        f"('{seen_paths[path]}' and '{from_expr}'). Each output path must be unique."
                    )
                seen_paths[path] = from_expr
        elif self.field_renames:
            targets: dict[str, str] = {}
            for source_field, target in self.field_renames.items():
                if target in targets and targets[target] != source_field:
                    raise ValueError(
                        f"Invalid config: rename target '{target}' is used by multiple fields "
                        f"('{targets[target]}' and '{source_field}'). Each rename target must be unique."
                    )
                targets[target] = source_field

    def project(self, record: dict[str, Any]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        normalizer = Normalizer()

        if self.fields:
            # Rich runtime projection configuration
            path_map: dict[str, str] = {}  # canonical root field -> renamed output path
            for field_cfg in self.fields:
                path = field_cfg.get("path")
                if not path:
                    continue
                from_expr = field_cfg.get("from") or path
                required = field_cfg.get("required", False)
                norm_rule = field_cfg.get("normalize")

                root_field = self._root_field(from_expr)
                if root_field:
                    path_map[root_field] = path

                value = self._extract_value(record, from_expr)

                # Apply normalization override if requested
                if value is not None:
                    if norm_rule == "E164":
                        if isinstance(value, list):
                            value = [normalizer._normalize_phone(v) for v in value if v]
                        else:
                            value = normalizer._normalize_phone(value)
                    elif norm_rule == "canonical":
                        if isinstance(value, list):
                            # canonicalize list of strings
                            value = normalizer._normalize_list(value)
                        else:
                            norm_lst = normalizer._normalize_list([value])
                            value = norm_lst[0] if norm_lst else None

                # Handle missing values
                if value in (None, "", [], {}):
                    if required and self.on_missing == "error":
                        raise ValueError(f"Missing required field: {path}")
                    if self.on_missing == "null":
                        output[path] = None
                    continue

                output[path] = value

            # Control inclusion of overall engines
            if self.include_confidence:
                if "overall_confidence" in record:
                    output["overall_confidence"] = record["overall_confidence"]
                if "field_confidence" in record:
                    output["field_confidence"] = {
                        path_map.get(field, field): score
                        for field, score in record["field_confidence"].items()
                    }
            else:
                output.pop("overall_confidence", None)
                output.pop("field_confidence", None)

            if self.include_provenance and "provenance" in record:
                output["provenance"] = [
                    {**entry, "field": path_map.get(entry["field"], entry["field"])}
                    for entry in record["provenance"]
                ]
            else:
                output.pop("provenance", None)

            if self.include_metadata and "metadata" in record:
                output["metadata"] = record["metadata"]
            else:
                output.pop("metadata", None)

        else:
            # Fallback to legacy configuration
            fields = self.selected_fields or list(record.keys())
            for field in fields:
                if field not in record or record[field] in (None, "", [], {}):
                    if self.on_missing == "error":
                        raise ValueError(f"Missing required field: {field}")
                    if self.on_missing == "null":
                        output[self.field_renames.get(field, field)] = None
                    continue
                output[self.field_renames.get(field, field)] = record[field]
            
            if not self.include_confidence:
                output.pop("overall_confidence", None)
                output.pop("field_confidence", None)
            elif "field_confidence" in output and self.field_renames:
                output["field_confidence"] = {
                    self.field_renames.get(field, field): score
                    for field, score in output["field_confidence"].items()
                }
            if not self.include_provenance:
                output.pop("provenance", None)
            elif "provenance" in output and self.field_renames:
                output["provenance"] = [
                    {**entry, "field": self.field_renames.get(entry["field"], entry["field"])}
                    for entry in output["provenance"]
                ]
            if not self.include_metadata:
                output.pop("metadata", None)

        if self.on_missing == "omit":
            output = self._clean_omitted_values(output)

        return output

    def _clean_omitted_values(self, val: Any) -> Any:
        if isinstance(val, dict):
            cleaned = {}
            for k, v in val.items():
                cv = self._clean_omitted_values(v)
                if cv not in (None, "", [], {}):
                    cleaned[k] = cv
            return cleaned
        elif isinstance(val, list):
            cleaned_list = []
            for item in val:
                cv = self._clean_omitted_values(item)
                if cv not in (None, "", [], {}):
                    cleaned_list.append(cv)
            return cleaned_list
        return val

    def _root_field(self, from_expr: str) -> str | None:
        """Extract the canonical root field name from a 'from' expression,
        e.g. 'skills[].name' -> 'skills', 'emails[0]' -> 'emails', 'full_name' -> 'full_name'."""
        if not from_expr:
            return None
        return re.split(r"[.\[]", from_expr, maxsplit=1)[0] or None

    def _extract_value(self, record: dict[str, Any], from_expr: str) -> Any:
        if not from_expr:
            return None

        # Handle list mapping: "skills[].name"
        if "[]." in from_expr:
            parts = from_expr.split("[].")
            list_key = parts[0]
            sub_key = parts[1]
            lst = record.get(list_key)
            if isinstance(lst, list):
                res = []
                for item in lst:
                    if isinstance(item, dict) and sub_key in item:
                        res.append(item[sub_key])
                    elif hasattr(item, sub_key):
                        res.append(getattr(item, sub_key))
                return res
            return []

        # Handle index extraction: "emails[0]"
        idx_match = re.match(r"^(\w+)\[(\d+)\]$", from_expr)
        if idx_match:
            key = idx_match.group(1)
            idx = int(idx_match.group(2))
            lst = record.get(key)
            if isinstance(lst, list) and idx < len(lst):
                return lst[idx]
            return None

        # Default fallback
        return record.get(from_expr)
