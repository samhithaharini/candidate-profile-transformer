from __future__ import annotations

from typing import Any
from models.candidate_schema import validate_candidate


class Validator:
    def validate(self, record: dict[str, Any], on_missing: str = "null") -> dict[str, Any]:
        if on_missing == "error":
            missing_paths = self._has_empty_structures(record)
            if missing_paths:
                missing_str = ", ".join(sorted(set(missing_paths)))
                raise ValueError(f"Missing or null values found in fields: {missing_str}")

        if self._is_canonical_shape(record):
            # Strict validation against Pydantic CanonicalCandidate
            try:
                candidate = validate_candidate(record)
                if on_missing == "omit":
                    dump = candidate.model_dump(exclude_none=True)
                    return self._clean_empty_structures(dump)
                else:
                    return candidate.model_dump()
            except (ValidationError, ValueError) as e:
                self._validate_projected_fields(record)
                if on_missing == "omit":
                    return self._clean_empty_structures(record)
                return record
        else:
            # Type checks for projected records
            self._validate_projected_fields(record)
            if on_missing == "omit":
                return self._clean_empty_structures(record)
            return record

    def _has_empty_structures(self, val: Any, path: str = "") -> list[str]:
        missing_paths = []
        if val in (None, "", [], {}):
            missing_paths.append(path or "root")
        elif isinstance(val, dict):
            for k, v in val.items():
                p = f"{path}.{k}" if path else k
                missing_paths.extend(self._has_empty_structures(v, p))
        elif isinstance(val, list):
            for idx, item in enumerate(val):
                # Don't add index if it's a simple primitive list that is empty, 
                # but if the list has empty items, indicate the array path
                p = f"{path}[{idx}]" if path else f"root[{idx}]"
                missing_paths.extend(self._has_empty_structures(item, p))
        return missing_paths

    def _clean_empty_structures(self, val: Any) -> Any:
        if isinstance(val, dict):
            cleaned = {}
            for k, v in val.items():
                cv = self._clean_empty_structures(v)
                if cv not in (None, "", [], {}, "null", "NULL", "None") and str(cv).lower() != "nan":
                    cleaned[k] = cv
            return cleaned
        elif isinstance(val, list):
            cleaned_list = []
            for item in val:
                cv = self._clean_empty_structures(item)
                if cv not in (None, "", [], {}, "null", "NULL", "None") and str(cv).lower() != "nan":
                    cleaned_list.append(cv)
            return cleaned_list
        return val

    def _is_canonical_shape(self, record: dict[str, Any]) -> bool:
        # If required canonical fields are missing, it's a projected record
        required_fields = ["candidate_id", "full_name", "emails", "overall_confidence"]
        if not all(field in record for field in required_fields):
            return False

        # If links is present and is a list or string, it's projected (canonical is a dict/LinksSchema)
        if "links" in record and not isinstance(record["links"], dict) and record["links"] is not None:
            return False
            
        # If skills is present and has elements, check if they are strings (projected)
        if "skills" in record and isinstance(record["skills"], list) and len(record["skills"]) > 0:
            if isinstance(record["skills"][0], str):
                return False
                
        # If experience has elements, check if they are strings (projected)
        if "experience" in record and isinstance(record["experience"], list) and len(record["experience"]) > 0:
            if isinstance(record["experience"][0], str):
                return False

        # If education has elements, check if they are strings (projected)
        if "education" in record and isinstance(record["education"], list) and len(record["education"]) > 0:
            if isinstance(record["education"][0], str):
                return False
                
        return True

    def _validate_projected_fields(self, record: dict[str, Any]) -> None:
        for str_field in ["candidate_id", "full_name", "headline"]:
            if str_field in record and record[str_field] is not None:
                if not isinstance(record[str_field], str):
                    raise ValueError(f"Field '{str_field}' must be a string, got {type(record[str_field])}")

        for list_field in ["emails", "phones", "skills", "experience", "education", "provenance"]:
            if list_field in record and record[list_field] is not None:
                if not isinstance(record[list_field], list):
                    raise ValueError(f"Field '{list_field}' must be a list, got {type(record[list_field])}")


from pydantic import ValidationError
