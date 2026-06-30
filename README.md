# Candidate Transformer

A production-quality Python candidate data ingestion and transformation platform. It reads data from multiple structured (Recruiter CSV, ATS JSON) and unstructured (Resume PDF, LinkedIn JSON, GitHub JSON, Recruiter Notes TXT) sources, matches, merges, validates, and projects them into customizable target shapes.

## Architecture

This project is organized as a clean 3-layered system:
1. **Presentation Layer**: 
   - `app.py`: A premium Streamlit web application.
   - `main.py`: Backward-compatible CLI command-line entrypoint.
2. **Application Layer**: 
   - `engine/pipeline.py`: Reusable `PipelineController` orchestrating execution and log capture (also usable directly from Python without the UI).
3. **Engine Layer**:
   - `parsers/`: Modular parser classes for CSV, PDF (via `pdfplumber`), LinkedIn/GitHub JSON, and Recruiter TXT notes.
   - `engine/`: Normalizer, Matcher, Merger, Confidence, Provenance, and Projector modules.
   - `schemas/`: Pydantic candidate schema definition.

## Installation

1. Create a Python 3.12+ environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run Web Interface (Streamlit)

Launch the interactive presentation layer:
```bash
streamlit run app.py
```

## Run Programmatically (no UI)

The pipeline is also fully usable as a plain Python module, with no Streamlit dependency, which is what the Streamlit UI itself calls under the hood:

```python
from pathlib import Path
import json
from engine.pipeline import PipelineController

config = json.loads(Path("config/config.json").read_text())
controller = PipelineController()
result = controller.run_pipeline(
    structured_path=Path("sample_data/recruiter.csv"),
    unstructured_path=Path("sample_data/resume.pdf"),
    structured_type="csv",        # "csv" | "json" (ATS JSON)
    unstructured_type="pdf",      # "pdf" | "linkedin_json" | "github_json" | "txt"
    config=config,
)
print(json.dumps(result["projected_output"], indent=2))
```

`result["success"]` is `False` with `result["error"]` set if any stage fails (missing/garbage source, no candidate match, schema validation failure, etc.) instead of raising — this is the thin input/output surface the assignment asks for, with the Streamlit app as the optional UI layer on top of it.

## Scope notes

- Each run takes exactly one structured source + one unstructured source (the minimum required by the brief). Combining more than two sources at once is intentionally out of scope given the time budget.
- OCR for scanned/image-only PDFs, live GitHub API rate-limit handling, and multi-language NLP on resume text are explicitly descoped — these fail the run with a clear error rather than silently fabricating data.
