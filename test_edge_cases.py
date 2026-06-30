import unittest
import json
import shutil
from pathlib import Path
from typing import Any

from engine.pipeline import PipelineController
from engine.extractor import Extractor, ExtractionError
from parsers.csv_parser import CsvParser, CsvParserError
from parsers.ats_json_parser import AtsJsonParser, AtsJsonParserError
from parsers.resume_parser import ResumeParser, ResumeParserError
from engine.normalizer import Normalizer
from engine.matcher import Matcher
from engine.validator import Validator


class TestCandidateTransformerEdgeCases(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for tests within the workspace
        self.test_dir = Path("temp_test_data")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        # Clean up temp test files
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def write_file(self, filename: str, content: str | bytes) -> Path:
        path = self.test_dir / filename
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_bytes(content)
        return path

    # --- 1. Ingestion / Detection Edge Cases ---

    def test_missing_files(self):
        # Test missing structured/unstructured files
        extractor = Extractor(
            Path("non_existent_file.csv"),
            Path("non_existent_file.pdf"),
            "csv",
            "pdf"
        )
        with self.assertRaises(ExtractionError) as ctx:
            extractor.extract()
        self.assertIn("not found", str(ctx.exception))

    def test_zero_byte_files(self):
        # Test empty CSV
        empty_csv = self.write_file("empty.csv", "")
        parser = CsvParser(empty_csv)
        with self.assertRaises(CsvParserError) as ctx:
            parser.parse()
        self.assertIn("empty", str(ctx.exception))

        # Test empty JSON
        empty_json = self.write_file("empty.json", "")
        parser = AtsJsonParser(empty_json)
        with self.assertRaises(AtsJsonParserError) as ctx:
            parser.parse()
        self.assertIn("empty", str(ctx.exception))

    def test_wrong_file_extensions(self):
        # Test wrong extensions validation in Extractor
        csv_file = self.write_file("data.csv", "name,email\nJohn,john@example.com")
        pdf_file = self.write_file("doc.pdf", b"%PDF-1.4...")
        
        # Pass PDF to CSV type
        extractor = Extractor(pdf_file, pdf_file, "csv", "pdf")
        with self.assertRaises(ExtractionError) as ctx:
            extractor.extract()
        self.assertIn("Wrong file extension", str(ctx.exception))

        # Pass CSV to PDF type
        extractor = Extractor(csv_file, csv_file, "csv", "pdf")
        with self.assertRaises(ExtractionError) as ctx:
            extractor.extract()
        self.assertIn("Wrong file extension", str(ctx.exception))

    def test_encoding_issues_and_smart_quotes(self):
        # CSV in CP1252 with smart quotes
        # “smart quotes” in CP1252
        csv_content = "name,email,phone\n“José Doe”,jose@example.com,+15551234567"
        csv_bytes = csv_content.encode("cp1252")
        cp1252_csv = self.write_file("cp1252.csv", csv_bytes)

        parser = CsvParser(cp1252_csv)
        data = parser.parse()
        # Smart quotes should be replaced and José should parse correctly
        self.assertEqual(data["name"], 'José Doe')
        self.assertEqual(data["email"], "jose@example.com")

    # --- 2. Extraction Edge Cases ---

    def test_ats_json_nested_objects_scalarize(self):
        # Test deep scalarization of nested ATS JSON structures
        ats_data = {
            "name": [{"value": "  Jane Doe  "}],
            "email": {"primary": "jane@example.com"},
            "phone": [[{"number": "+15559876543"}]],
            "current_company": {"value": {"name": "Google"}}
        }
        json_file = self.write_file("ats.json", json.dumps(ats_data))
        parser = AtsJsonParser(json_file)
        data = parser.parse()
        self.assertEqual(data["name"], "Jane Doe")
        self.assertEqual(data["email"], "jane@example.com")
        self.assertEqual(data["phone"], "+15559876543")
        self.assertEqual(data["current_company"], "Google")

    def test_resume_parser_flexible_headers(self):
        # Test multi-column layout or bullet list headers (optional space/bullets before header)
        resume_text = """
        • SKILLS
        Python, JavaScript, ML
        
          EXPERIENCE
        Software Engineer at Google
        """
        # Create a dummy text notes structure to test the parsing logic directly (ResumeParser uses pdfplumber, 
        # so we test the flexible regex logic which is identical in RecruiterNotesParser)
        txt_file = self.write_file("notes.txt", resume_text)
        from parsers.recruiter_notes_parser import RecruiterNotesParser
        parser = RecruiterNotesParser(txt_file)
        data = parser.parse()
        self.assertIn("Python", data["skills"])
        self.assertIn("Software Engineer at Google", data["experience"])

    # --- 3. Normalization Edge Cases ---

    def test_phone_normalization_with_extensions(self):
        normalizer = Normalizer()
        # Phone with extension
        self.assertEqual(normalizer._normalize_phone("+1 650-253-0000 ext 123"), "+16502530000")
        self.assertEqual(normalizer._normalize_phone("+16502530000 x456"), "+16502530000")
        # Fake phone number
        self.assertIsNone(normalizer._normalize_phone("123-456-7890"))

    def test_date_normalization(self):
        normalizer = Normalizer()
        # Two digit years
        self.assertEqual(normalizer.normalize_dates("Jan 20"), "2020-01")
        # Commas and spacing
        self.assertEqual(normalizer.normalize_dates("January, 2020"), "2020-01")
        # Present variations
        self.assertEqual(normalizer.normalize_dates("Currently working"), "Present")
        self.assertEqual(normalizer.normalize_dates("currently"), "Present")

    def test_country_aliases(self):
        normalizer = Normalizer()
        self.assertEqual(normalizer._normalize_country("spain"), "ES")
        self.assertEqual(normalizer._normalize_country("china"), "CN")
        self.assertEqual(normalizer._normalize_country("united states of america"), "US")

    # --- 4. Merge / Conflict Resolution Edge Cases ---

    def test_non_latin_names_matching(self):
        matcher = Matcher()
        # Chinese name preservation
        self.assertTrue(matcher.match(
            {"full_name": "李雷", "emails": ["lilei@example.com"]},
            {"full_name": "李雷", "emails": ["lilei@example.com"]}
        ).matched)
        
        self.assertAlmostEqual(matcher._match_name("José", "Jose"), 1.0)
        self.assertAlmostEqual(matcher._match_name("李雷", "李雷"), 1.0)

    def test_duplicate_names_company_and_identifier_checks(self):
        matcher = Matcher()
        # Same name but conflicting emails -> should reject match
        self.assertFalse(matcher.match(
            {"full_name": "John Smith", "emails": ["john1@gmail.com"]},
            {"full_name": "John Smith", "emails": ["john2@yahoo.com"]}
        ).matched)

        # Same name, no email conflict, but conflicting companies -> should reject match
        self.assertFalse(matcher.match(
            {"full_name": "John Smith", "metadata": {"company": "Google"}, "experience": []},
            {"full_name": "John Smith", "metadata": {"company": "Microsoft"}, "experience": []}
        ).matched)

        # Same name, no email conflict, company is missing in one -> should match
        self.assertTrue(matcher.match(
            {"full_name": "John Smith", "metadata": {"company": "Google"}, "experience": []},
            {"full_name": "John Smith", "metadata": {}, "experience": []}
        ).matched)

    # --- 5. Validation / Output Edge Cases ---

    def test_validation_on_missing_policy(self):
        validator = Validator()
        record_with_missing_fields = {
            "candidate_id": "test_id",
            "full_name": None,  # Required by CanonicalCandidate Pydantic model
            "emails": None,
            "overall_confidence": 0.95
        }

        # Policy "error" -> should raise ValueError
        with self.assertRaises(ValueError):
            validator.validate(record_with_missing_fields, on_missing="error")

        # Policy "null" -> should return record with null values, not crash
        res_null = validator.validate(record_with_missing_fields, on_missing="null")
        self.assertIsNone(res_null["full_name"])

        # Policy "omit" -> should return record with key omitted, not crash
        res_omit = validator.validate(record_with_missing_fields, on_missing="omit")
        self.assertNotIn("full_name", res_omit)

    # --- 6. Real-world Parsing Verification ---

    def test_real_world_extracted_parsing(self):
        # Text block mimicking Samhitha's resume
        resume_text = """
        SAMHITHA HARINI V
        samhitha2613 @gmail.com | +919865576818 | linkedin.com/in/samhitha-harini-v | github.com/samhithaharini
        
        KEY SKILLS
        Programming Languages: Python, Java, SQL
        
        INTERNSHIP EXPERIENCE
        SOFTWARE DEVELOPER INTERN | INTERNBOOT 09/2025 – 10/2025
        Worked on Python-based machine learning workflows.
        """
        txt_file = self.write_file("samhitha.txt", resume_text)
        from parsers.recruiter_notes_parser import RecruiterNotesParser
        parser = RecruiterNotesParser(txt_file)
        data = parser.parse()
        
        # Verify email space stripping
        self.assertEqual(data["email"], "samhitha2613@gmail.com")
        
        # Verify skills extraction via KEY SKILLS header
        self.assertTrue(any("Python" in s for s in data["skills"]))
        
        # Verify experience extraction via INTERNSHIP EXPERIENCE header
        self.assertTrue(any("SOFTWARE DEVELOPER" in e for e in data["experience"]))
        
        # Verify links extraction without http/www prefix
        self.assertIn("linkedin.com/in/samhitha-harini-v", data["links"])
        self.assertIn("github.com/samhithaharini", data["links"])


if __name__ == "__main__":
    unittest.main()
