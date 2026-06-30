from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any
from uuid import uuid5, NAMESPACE_DNS

from engine.extractor import Extractor
from engine.normalizer import Normalizer
from engine.matcher import Matcher, MatchResult
from engine.merger import Merger
from engine.confidence import ConfidenceEngine
from engine.provenance import ProvenanceEngine
from engine.projector import Projector
from engine.validator import Validator
from utils.logger import get_logger


class PipelineController:
    def run_pipeline(
        self,
        structured_path: Path,
        unstructured_path: Path,
        structured_type: str,
        unstructured_type: str,
        config: dict[str, Any]
    ) -> dict[str, Any]:
        # 1. Setup log capture
        logger = get_logger("candidate_transformer")
        log_capture = io.StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(log_handler)

        try:
            logger.info("Initializing transformation pipeline")
            logger.info(f"Structured Source: {structured_path.name} (type: {structured_type})")
            logger.info(f"Unstructured Source: {unstructured_path.name} (type: {unstructured_type})")

            # 2. Extraction
            logger.info("Step 1: Extracting candidate entities")
            extractor = Extractor(
                structured_path,
                unstructured_path,
                structured_type,
                unstructured_type
            )
            extracted = extractor.extract()

            # 3. Normalization
            logger.info("Step 2: Normalizing data")
            normalizer = Normalizer()
            structured_norm = normalizer.normalize_record(extracted["structured"])
            unstructured_norm = normalizer.normalize_record(extracted["unstructured"])

            # 4. Matching
            logger.info("Step 3: Matching candidate records")
            matcher = Matcher()
            match_result: MatchResult = matcher.match(structured_norm, unstructured_norm)
            
            if not match_result.matched:
                logger.warning(f"Matching failed: structured and unstructured records do not match. Reason: {match_result.reason}")
                raise ValueError(f"Candidate mismatch: {match_result.reason}")
            logger.info(f"Candidate records matched successfully (Reason: {match_result.reason}, Score: {match_result.score})")

            # 5. Merging
            logger.info("Step 4: Merging candidate records")
            merger = Merger()
            merged, merge_reasons = merger.merge_with_reasons(structured_norm, unstructured_norm)

            # Generate candidate ID based on email/name to keep it deterministic
            candidate_id = self._generate_candidate_id(merged)
            merged["candidate_id"] = candidate_id

            # 6. Confidence Scoring
            logger.info("Step 5: Calculating field confidence scores")
            confidence_engine = ConfidenceEngine()
            field_scores = confidence_engine.score_fields(structured_norm, unstructured_norm, merged)
            overall_score = confidence_engine.overall_confidence(field_scores)
            merged["field_confidence"] = field_scores
            merged["overall_confidence"] = overall_score

            # 7. Provenance Tracking
            logger.info("Step 6: Generating data provenance")
            provenance_engine = ProvenanceEngine()
            provenance = provenance_engine.build_provenance(
                merged, merge_reasons, structured_norm, unstructured_norm
            )
            merged["provenance"] = provenance

            # Compile full canonical profile
            canonical_profile = {
                "candidate_id": candidate_id,
                "full_name": merged.get("full_name") or "",
                "emails": merged.get("emails", []),
                "phones": merged.get("phones", []),
                "location": merged.get("location"),
                "links": merged.get("links"),
                "headline": merged.get("headline"),
                "years_experience": merged.get("years_experience"),
                "skills": merged.get("skills", []),
                "experience": merged.get("experience", []),
                "education": merged.get("education", []),
                "field_confidence": field_scores,
                "overall_confidence": overall_score,
                "provenance": provenance,
                "metadata": {
                    "structured_metadata": structured_norm.get("metadata"),
                    "unstructured_metadata": unstructured_norm.get("metadata"),
                    "match_reason": match_result.reason,
                    "match_score": match_result.score,
                },
            }

            # 8. Projection
            logger.info("Step 7: Applying projection layer")
            projector = Projector(config)
            projected = projector.project(canonical_profile)

            # 9. Schema Validation
            logger.info("Step 8: Validating output against schema")
            validator = Validator()
            validated_output = validator.validate(projected, config.get("on_missing", "null"))

            logger.info("Pipeline execution completed successfully")
            
            return {
                "success": True,
                "canonical_profile": canonical_profile,
                "projected_output": validated_output,
                "provenance": provenance,
                "confidence_scores": field_scores,
                "overall_confidence": overall_score,
                "match_result": {
                    "matched": match_result.matched,
                    "score": match_result.score,
                    "reason": match_result.reason
                },
                "logs": log_capture.getvalue()
            }

        except Exception as error:
            logger.error(f"Pipeline failed: {error}")
            return {
                "success": False,
                "error": str(error),
                "logs": log_capture.getvalue()
            }
            
        finally:
            logger.removeHandler(log_handler)

    def _generate_candidate_id(self, record: dict[str, Any]) -> str:
        # Create deterministic UUID based on first email or name
        emails = record.get("emails") or []
        email = emails[0] if emails else None
        name = record.get("full_name") or "unknown"
        seed = email if email else name
        return str(uuid5(NAMESPACE_DNS, f"candidate:{seed}"))
