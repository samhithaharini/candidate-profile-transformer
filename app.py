import streamlit as st
import json
import tempfile
import pandas as pd
from pathlib import Path
from typing import Any

from engine.pipeline import PipelineController
from parsers.csv_parser import CsvParser
from parsers.ats_json_parser import AtsJsonParser
from parsers.resume_parser import ResumeParser
from parsers.linkedin_json_parser import LinkedInJsonParser
from parsers.github_json_parser import GitHubJsonParser
from parsers.recruiter_notes_parser import RecruiterNotesParser
from providers import LinkedInProvider, GitHubProvider, ValidationError


# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Multi-Source Candidate Data Transformer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN PREMIUM CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    /* Global theme overrides */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }
    
    /* Sidebar custom styling (dark slate/white) */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] li {
        color: #FFFFFF !important;
    }
    
    /* Sidebar form input elements */
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select, [data-testid="stSidebar"] div[role="listbox"] {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        border: 1px solid #334155 !important;
    }

    h1, h2, h3, h4 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #0F172A;
    }
    
    .main-title {
        color: #1E3A8A !important;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0.3rem;
    }
    
    .subtitle {
        color: #475569;
        font-size: 1.15rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Section Headers */
    .section-header {
        font-family: 'Outfit', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: #1E3A8A !important;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 0.5rem;
        margin-bottom: 1.2rem;
    }
    
    /* Sleek border container wrappers */
    [data-testid="element-container"] div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        background-color: #F8FAFC !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        padding: 1.5rem !important;
    }
    
    /* File uploader custom style */
    [data-testid="stFileUploader"] {
        border: none !important;
        padding: 0 !important;
    }
    [data-testid="stFileUploader"] > section {
        border: 2px dashed #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 1.5rem !important;
        background-color: #FFFFFF !important;
        transition: border-color 0.2s ease-in-out;
    }
    [data-testid="stFileUploader"] > section:hover {
        border-color: #1E3A8A !important;
    }
    [data-testid="stFileUploader"] label, [data-testid="stFileUploader"] p, [data-testid="stFileUploader"] span {
        color: #475569 !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: #1E3A8A !important;
        color: white !important;
        border-radius: 6px !important;
        border: none !important;
        padding: 0.4rem 1rem !important;
        transition: background-color 0.2s;
    }
    [data-testid="stFileUploader"] button:hover {
        background-color: #172554 !important;
    }
    
    /* Fix button text color */
    [data-testid="stFileUploader"] button,
    [data-testid="stFileUploader"] button * {
        color: white !important;
    }
    
    /* Uploaded file name text color visibility */
    [data-testid="stUploadedFile"] {
        background-color: #1E3A8A !important;
        border-radius: 6px !important;
    }
    [data-testid="stUploadedFile"],
    [data-testid="stUploadedFile"] * {
        color: white !important;
    }

    
    /* Text input custom style */
    .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        padding: 0.55rem 1rem !important;
        background-color: #FFFFFF !important;
        font-size: 0.95rem !important;
        color: #0F172A !important;
        transition: border-color 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1E3A8A !important;
        box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.15) !important;
    }
    
    /* Custom tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        border-bottom: 1.5px solid #E2E8F0 !important;
        padding-left: 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F1F5F9 !important;
        border: 1px solid #E2E8F0 !important;
        border-bottom: none !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 8px 20px !important;
        font-weight: 600 !important;
        color: #64748B !important;
        transition: all 0.2s ease-in-out;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #1E3A8A !important;
        background-color: #E2E8F0 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        border-color: #E2E8F0 #E2E8F0 #FFFFFF !important;
        color: #1E3A8A !important;
        font-weight: 700 !important;
        box-shadow: 0 -2px 0 #1E3A8A inset !important;
    }
    
    /* Card design */
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.03);
        transition: transform 0.2s, box-shadow 0.2s;
        margin-bottom: 1rem;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.08);
        border-color: #CBD5E1;
    }
    
    .metric-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0F172A;
    }
    
    /* Run Transformation Button */
    div.stButton > button:first-child,
    div.stDownloadButton > button {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%) !important;
        color: white !important;
        border: none;
        padding: 0.8rem 2.2rem;
        border-radius: 10px;
        font-weight: 600;
        font-size: 1.05rem;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.25);
        transition: all 0.3s;
        width: 100%;
    }
    div.stButton > button:first-child:hover,
    div.stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(30, 58, 138, 0.35);
    }
    div.stDownloadButton > button p {
        color: white !important;
    }

    /* Success notification style */
    div[data-testid="stNotification"] {
        background-color: #E8F5E9 !important;
        color: #1B5E20 !important;
        border: 1.5px solid #C8E6C9 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stNotification"] p {
        color: #1B5E20 !important;
        font-weight: 600 !important;
    }
</style>

""", unsafe_allow_html=True)


# --- HELPERS ---
def save_uploaded_file(uploaded_file) -> Path:
    # Save uploaded file to temp file
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getvalue())
        return Path(temp_file.name)


def parse_and_preview(file_path: Path, source_type: str) -> dict[str, Any] | None:
    try:
        if source_type == "csv":
            return CsvParser(file_path).parse()
        elif source_type == "ats_json":
            return AtsJsonParser(file_path).parse()
        elif source_type == "resume_pdf":
            return ResumeParser(file_path).parse()
        elif source_type in ("linkedin_json", "linkedin_profile"):
            return LinkedInJsonParser(file_path).parse()
        elif source_type in ("github_json", "github_profile"):
            return GitHubJsonParser(file_path).parse()
        elif source_type == "recruiter_notes":
            return RecruiterNotesParser(file_path).parse()
    except Exception as e:
        st.error(f"Error parsing preview: {e}")
    return None


def list_zip_contents(uploaded_file, unstruct_type: str) -> list[tuple[str, int]]:
    import zipfile
    import io
    files = []
    try:
        zip_data = io.BytesIO(uploaded_file.getvalue())
        with zipfile.ZipFile(zip_data, 'r') as zip_ref:
            for info in zip_ref.infolist():
                if not info.is_dir():
                    ext = Path(info.filename).suffix.lower()
                    if unstruct_type == "resume_pdf" and ext == ".pdf":
                        files.append((Path(info.filename).name, info.file_size))
                    elif unstruct_type == "recruiter_notes" and ext == ".txt":
                        files.append((Path(info.filename).name, info.file_size))
                    elif unstruct_type in ("linkedin_profile", "github_profile") and ext == ".json":
                        files.append((Path(info.filename).name, info.file_size))
    except Exception:
        pass
    return files


def parse_and_preview_zip(zip_path: Path, unstruct_type: str) -> dict[str, Any] | None:
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for name in zip_ref.namelist():
                ext = Path(name).suffix.lower()
                is_match = False
                if unstruct_type == "resume_pdf" and ext == ".pdf":
                    is_match = True
                elif unstruct_type == "recruiter_notes" and ext == ".txt":
                    is_match = True
                elif unstruct_type in ("linkedin_profile", "github_profile") and ext == ".json":
                    is_match = True
                
                if is_match:
                    with tempfile.TemporaryDirectory() as td:
                        extracted_path = zip_ref.extract(name, td)
                        return parse_and_preview(Path(extracted_path), unstruct_type)
    except Exception:
        pass
    return None


def get_adjusted_profile(unstruct_type: str, url: str, struct_path: Path | None, struct_type: str) -> dict[str, Any]:
    # 1. Load mock data from provider
    if unstruct_type == "linkedin_profile":
        raw_data = LinkedInProvider().get_profile(url)
    else:
        raw_data = GitHubProvider().get_profile(url)
        
    # 2. Try to adjust profile if structured data is loaded
    if struct_path and struct_path.exists():
        try:
            # Parse structured source
            struct_data = parse_and_preview(struct_path, struct_type)
            if struct_data:
                # Extract name, email, phone from structured source
                name = struct_data.get("name")
                email = struct_data.get("email")
                phone = struct_data.get("phone")
                
                # If structured contains lists/objects, handle appropriately
                if isinstance(email, list) and email:
                    email = email[0]
                if isinstance(phone, list) and phone:
                    phone = phone[0]
                    
                # Overwrite mock details to match the structured candidate
                if name:
                    raw_data["name"] = name
                if email:
                    raw_data["email"] = email
                if phone:
                    raw_data["phone"] = phone
        except Exception:
            pass # Ignore adjustments on failure and use raw mock data
            
    return raw_data


# --- HEADER ---
st.markdown('<div class="main-title">Multi-Source Candidate Data Transformer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Ingest, normalize, match, and merge structured & unstructured profile sources into verified canonical records.</div>', unsafe_allow_html=True)

# --- SIDEBAR CONFIGURATION ---
st.sidebar.markdown("""
<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 5px; padding-top: 10px;">
    <div style="background-color: #10B981; border-radius: 8px; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(16, 185, 129, 0.3);">
        <span style="color: white; font-size: 1.3rem; font-weight: bold;">⚡</span>
    </div>
    <span style="font-family: 'Outfit', sans-serif; font-size: 1.45rem; font-weight: 700; color: #FFFFFF;">Candidate Transformer</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

st.sidebar.markdown("### OUTPUT FIELDS")
show_name = st.sidebar.checkbox("Full Name", value=True)
show_email = st.sidebar.checkbox("Email", value=True)
show_phone = st.sidebar.checkbox("Phone", value=True)
show_location = st.sidebar.checkbox("Location", value=True)
show_headline = st.sidebar.checkbox("Headline / Title", value=True)
show_skills = st.sidebar.checkbox("Skills", value=True)
show_experience = st.sidebar.checkbox("Work Experience", value=True)
show_education = st.sidebar.checkbox("Education", value=True)

st.sidebar.markdown("---")

st.sidebar.markdown("### INPUT CONFIGURATION")
structured_format = st.sidebar.selectbox(
    "Choose Structured Source Type",
    options=["Recruiter CSV", "ATS JSON"],
    index=0
)
unstructured_format = st.sidebar.selectbox(
    "Choose Unstructured Source Type",
    options=["Resume PDF", "LinkedIn Profile", "GitHub Profile", "Recruiter Notes TXT"],
    index=0
)

# Map string choices to internal identifiers
struct_map = {"Recruiter CSV": "csv", "ATS JSON": "ats_json"}
unstruct_map = {
    "Resume PDF": "resume_pdf",
    "LinkedIn Profile": "linkedin_profile",
    "GitHub Profile": "github_profile",
    "Recruiter Notes TXT": "recruiter_notes"
}

struct_type = struct_map[structured_format]
unstruct_type = unstruct_map[unstructured_format]

# Initialize session state for preloading URL values if not already present
if "linkedin_url_input" not in st.session_state:
    st.session_state.linkedin_url_input = ""
if "github_url_input" not in st.session_state:
    st.session_state.github_url_input = ""
if "prev_load_sample" not in st.session_state:
    st.session_state.prev_load_sample = False

load_sample = st.sidebar.checkbox(
    "Load Sample Input Files",
    value=st.session_state.get("load_sample_checkbox_val", False),
    help="Pre-fill values with sample candidate data (Jane Doe) for quick testing.",
    key="load_sample_checkbox_val"
)

if load_sample != st.session_state.prev_load_sample:
    st.session_state.prev_load_sample = load_sample
    if load_sample:
        st.session_state.linkedin_url_input = "https://www.linkedin.com/in/jane-doe/"
        st.session_state.github_url_input = "https://github.com/jane-doe"
    else:
        st.session_state.linkedin_url_input = ""
        st.session_state.github_url_input = ""

st.sidebar.markdown("---")
st.sidebar.markdown("### RUNTIME OPTIONS")

include_confidence = st.sidebar.checkbox("Include Confidence Scores", value=True)
include_provenance = st.sidebar.checkbox("Include Provenance Tracking", value=True)
include_metadata = st.sidebar.checkbox("Include Execution Metadata", value=True)

missing_policy = st.sidebar.radio(
    "Missing Field Policy (on_missing)",
    options=["null", "omit", "error"],
    index=0,
    help="Define system behavior when projected fields are missing in canonical output."
)

# Dynamically build projection config based on OUTPUT FIELDS checkboxes to satisfy PDF twists
fields_config = [{"path": "candidate_id", "required": True}]

if show_name:
    fields_config.append({"path": "full_name", "required": True})
if show_email:
    # PDF twist: Map emails list to primary_email (extract first element)
    fields_config.append({"path": "primary_email", "from": "emails[0]", "required": True})
if show_phone:
    # PDF twist: Map phones list to phone, normalize to E164 format
    fields_config.append({"path": "phone", "from": "phones[0]", "normalize": "E164"})
if show_location:
    fields_config.append({"path": "location"})
if show_headline:
    fields_config.append({"path": "headline"})
    fields_config.append({"path": "years_experience"})
if show_skills:
    # PDF twist: Map skills list to skills string list, normalize skill names to canonical
    fields_config.append({"path": "skills", "from": "skills[].name", "normalize": "canonical"})
if show_experience:
    fields_config.append({"path": "experience"})
if show_education:
    fields_config.append({"path": "education"})

# Always include links by default
fields_config.append({"path": "links"})

# Build pipeline config
pipeline_config = {
    "fields": fields_config,
    "include_confidence": include_confidence,
    "include_provenance": include_provenance,
    "include_metadata": include_metadata,
    "on_missing": missing_policy
}

# --- MAIN CONTENT LAYOUT ---
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### Upload Structured Source ({structured_format})")
    struct_files = st.file_uploader(
        f"Upload {structured_format} File(s)",
        type=["csv", "json"] if struct_type == "ats_json" else ["csv"],
        accept_multiple_files=True,
        key="struct_file_uploader"
    )
    if not struct_files and load_sample and struct_type == "csv":
        st.info("ℹ️ Using sample structured source: `sample_data/recruiter.csv` (Jane Doe)")

with col2:
    st.markdown(f"### Upload Unstructured Source ({unstructured_format})")
    
    unstruct_files = []
    unstruct_url = ""
    url_valid = True
    
    if unstruct_type == "resume_pdf":
        unstruct_files = st.file_uploader(
            "Upload Resume PDF(s) or ZIP Archive",
            type=["pdf", "zip"],
            accept_multiple_files=True,
            key="unstruct_file_uploader"
        )
        st.caption("💡 **Tip**: You can upload a single **.zip archive** containing all your PDF resumes, or select multiple PDFs at once using Ctrl/Shift+Click!")
    elif unstruct_type == "recruiter_notes":
        unstruct_files = st.file_uploader(
            "Upload Recruiter Notes TXT(s) or ZIP Archive",
            type=["txt", "zip"],
            accept_multiple_files=True,
            key="unstruct_file_uploader"
        )
        st.caption("💡 **Tip**: You can upload a single **.zip archive** containing all your TXT notes, or select multiple TXT files at once using Ctrl/Shift+Click!")
    elif unstruct_type == "linkedin_profile":
        unstruct_url = st.text_input(
            "LinkedIn Profile URL",
            placeholder="https://www.linkedin.com/in/example/",
            key="linkedin_url_input"
        )
        if unstruct_url:
            url_valid = LinkedInProvider.validate_url(unstruct_url)
            if not url_valid:
                st.error("❌ Invalid LinkedIn URL. Format: https://www.linkedin.com/in/<username>")
        unstruct_files = st.file_uploader(
            "Alternative: Upload LinkedIn JSON File(s) or ZIP Archive",
            type=["json", "zip"],
            accept_multiple_files=True,
            key="unstruct_file_uploader"
        )
        st.caption("💡 **Tip**: You can upload a single **.zip archive** containing multiple JSON profiles, or select multiple JSON files at once using Ctrl/Shift+Click!")
    elif unstruct_type == "github_profile":
        unstruct_url = st.text_input(
            "GitHub Profile URL",
            placeholder="https://github.com/example",
            key="github_url_input"
        )
        if unstruct_url:
            url_valid = GitHubProvider.validate_url(unstruct_url)
            if not url_valid:
                st.error("❌ Invalid GitHub URL. Format: https://github.com/<username>")
        unstruct_files = st.file_uploader(
            "Alternative: Upload GitHub JSON File(s) or ZIP Archive",
            type=["json", "zip"],
            accept_multiple_files=True,
            key="unstruct_file_uploader"
        )
        st.caption("💡 **Tip**: You can upload a single **.zip archive** containing multiple JSON profiles, or select multiple JSON files at once using Ctrl/Shift+Click!")

# Resolve paths and names for Structured Source
struct_paths = []
struct_loaded = False
struct_file_names = []
struct_file_sizes = []

if struct_files:
    for f in struct_files:
        if f.size == 0:
            st.warning(f"⚠️ Structured file '{f.name}' is empty and will be skipped.")
            continue
        struct_paths.append(save_uploaded_file(f))
        struct_file_names.append(f.name)
        struct_file_sizes.append(f.size)
    struct_loaded = len(struct_paths) > 0
elif load_sample and struct_type == "csv":
    p = Path("sample_data/recruiter.csv")
    struct_paths.append(p)
    struct_loaded = True
    struct_file_names.append("recruiter.csv")
    struct_file_sizes.append(p.stat().st_size)

# Resolve paths and names for Unstructured Source
unstruct_paths = []
unstruct_loaded = False
unstruct_file_names = []
unstruct_file_sizes = []

if unstruct_files:
    for f in unstruct_files:
        if f.size == 0:
            st.warning(f"⚠️ Unstructured file '{f.name}' is empty and will be skipped.")
            continue
        if f.name.lower().endswith(".zip"):
            zip_files = list_zip_contents(f, unstruct_type)
            for fn, sz in zip_files:
                unstruct_file_names.append(fn)
                unstruct_file_sizes.append(sz)
            unstruct_paths.append(save_uploaded_file(f))
        else:
            unstruct_paths.append(save_uploaded_file(f))
            unstruct_file_names.append(f.name)
            unstruct_file_sizes.append(f.size)
    unstruct_loaded = len(unstruct_file_names) > 0
else:
    if unstruct_type in ("linkedin_profile", "github_profile"):
        unstruct_loaded = bool(unstruct_url and url_valid)
    elif load_sample:
        if unstruct_type == "resume_pdf":
            p = Path("sample_data/resume.pdf")
            unstruct_paths.append(p)
            unstruct_file_names.append("resume.pdf")
            unstruct_file_sizes.append(p.stat().st_size)
            unstruct_loaded = True
        elif unstruct_type == "recruiter_notes":
            p = Path("sample_data/recruiter_notes.txt")
            unstruct_paths.append(p)
            unstruct_file_names.append("recruiter_notes.txt")
            unstruct_file_sizes.append(p.stat().st_size)
            unstruct_loaded = True

st.markdown("---")

# --- PREVIEWS REMOVED ---

if struct_loaded and unstruct_loaded:
    st.markdown("### Execute Transformation Engine")
    
    if st.button("Run Transformation Pipeline"):
        with st.spinner("Executing pipeline layers..."):
            run_struct_paths = struct_paths
            is_temp_struct = bool(struct_files)
                
            run_unstruct_paths = []
            run_unstruct_file_names = []
            is_temp_unstruct_list = []
            zip_temp_dirs = []
            
            try:
                if unstruct_type in ("linkedin_profile", "github_profile") and not unstruct_files:
                    raw_data = get_adjusted_profile(unstruct_type, unstruct_url, struct_paths[0] if struct_paths else None, struct_type)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                        temp_file.write(json.dumps(raw_data).encode("utf-8"))
                        run_unstruct_paths.append(Path(temp_file.name))
                        run_unstruct_file_names.append(f"{unstruct_type}_url")
                        is_temp_unstruct_list.append(True)
                else:
                    import zipfile
                    for p in unstruct_paths:
                        if p.name.lower().endswith(".zip"):
                            zip_dir = Path(tempfile.mkdtemp())
                            zip_temp_dirs.append(zip_dir)
                            with zipfile.ZipFile(p, 'r') as zip_ref:
                                zip_ref.extractall(zip_dir)
                            for extracted_file in zip_dir.rglob("*"):
                                if extracted_file.is_file():
                                    ext = extracted_file.suffix.lower()
                                    is_match = False
                                    if unstruct_type == "resume_pdf" and ext == ".pdf":
                                        is_match = True
                                    elif unstruct_type == "recruiter_notes" and ext == ".txt":
                                        is_match = True
                                    elif unstruct_type in ("linkedin_profile", "github_profile") and ext == ".json":
                                        is_match = True
                                    
                                    if is_match:
                                        run_unstruct_paths.append(extracted_file)
                                        run_unstruct_file_names.append(extracted_file.name)
                                        is_temp_unstruct_list.append(True)
                            if p.exists():
                                p.unlink()
                        else:
                            run_unstruct_paths.append(p)
                            original_idx = unstruct_paths.index(p)
                            fn = unstruct_file_names[original_idx] if original_idx < len(unstruct_file_names) else p.name
                            run_unstruct_file_names.append(fn)
                            is_temp_unstruct_list.append(bool(unstruct_files))
                
                controller = PipelineController()
                results = []
                success_count = 0
                failure_count = 0
                
                for idx, single_unstruct_path in enumerate(run_unstruct_paths):
                    fn = run_unstruct_file_names[idx]
                    try:
                        res = controller.run_pipeline(
                            structured_paths=run_struct_paths,
                            unstructured_path=single_unstruct_path,
                            structured_type=struct_type,
                            unstructured_type=unstruct_type,
                            config=pipeline_config
                        )
                        if res["success"]:
                            success_count += 1
                            results.append({
                                "candidate_number": idx + 1,
                                "file_name": fn,
                                "success": True,
                                "name": res["canonical_profile"].get("full_name") or "Unknown",
                                "score": res["match_result"].get("score", 0.0),
                                "reason": res["match_result"].get("reason", ""),
                                "result": res
                            })
                        else:
                            failure_count += 1
                            results.append({
                                "candidate_number": idx + 1,
                                "file_name": fn,
                                "success": False,
                                "name": "N/A",
                                "score": 0.0,
                                "reason": "N/A",
                                "error": res["error"],
                                "result": res
                            })
                    except Exception as e:
                        failure_count += 1
                        results.append({
                            "candidate_number": idx + 1,
                            "file_name": fn,
                            "success": False,
                            "name": "N/A",
                            "score": 0.0,
                            "reason": "N/A",
                            "error": str(e),
                            "result": None
                        })
                
                if is_temp_struct:
                    for p in run_struct_paths:
                        if p.exists():
                            p.unlink()
                for p, is_temp in zip(run_unstruct_paths, is_temp_unstruct_list):
                    if is_temp and p.exists() and not any(zip_dir in p.parents for zip_dir in zip_temp_dirs):
                        p.unlink()
                import shutil
                for zip_dir in zip_temp_dirs:
                    if zip_dir.exists():
                        shutil.rmtree(zip_dir)
                
                st.session_state.batch_results = results
                st.session_state.batch_success = success_count
                st.session_state.batch_failure = failure_count
                st.success(f"🎉 Batch processed! Success: {success_count}, Failures: {failure_count}")
                
            except Exception as ex:
                st.error(f"❌ Execution failed: {ex}")

# --- SECTION 6 & 7: DASHBOARD & VIEWER ---
if "batch_results" in st.session_state:
    results = st.session_state.batch_results
    success_count = st.session_state.batch_success
    failure_count = st.session_state.batch_failure
    
    st.markdown("---")
    st.markdown("### Processed Candidates Dashboard")
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Resumes</div>
            <div class="metric-value">{len(results)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_stat2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #10B981;">
            <div class="metric-title">Successfully Matched</div>
            <div class="metric-value" style="color: #10B981;">{success_count}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_stat3:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #EF4444;">
            <div class="metric-title">Failures / Mismatches</div>
            <div class="metric-value" style="color: #EF4444;">{failure_count}</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Bulk ZIP Download option
    success_results = [r for r in results if r["success"]]
    if success_results:
        import io
        import zipfile
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for r in success_results:
                filename = f"candidate_{r['candidate_number']}_{r['name'].replace(' ', '_')}.json"
                data_str = json.dumps(r["result"]["projected_output"], indent=2)
                zip_file.writestr(filename, data_str)
        
        st.download_button(
            label="📦 Download All Processed Profiles (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="batch_processed_profiles.zip",
            mime="application/zip"
        )
        
    st.markdown("#### Search and Filter Candidates")
    search_query = st.text_input("🔍 Fetch candidate by name or filename", placeholder="Type name or file to search...")
    
    filtered_results = []
    for r in results:
        if not search_query:
            filtered_results.append(r)
        else:
            name_match = search_query.lower() in r["name"].lower()
            file_match = search_query.lower() in r["file_name"].lower()
            if name_match or file_match:
                filtered_results.append(r)
                
    st.markdown(f"**Showing {len(filtered_results)} of {len(results)} candidate records**")
    
    table_data = []
    for r in filtered_results:
        status_str = "✅ Success" if r["success"] else f"❌ Failed: {r.get('error', 'Unknown Error')}"
        table_data.append({
            "No.": r["candidate_number"],
            "File Name": r["file_name"],
            "Matched Name": r["name"],
            "Match Score": f"{r['score'] * 100:.0f}%" if r["success"] else "0%",
            "Match Reason": r["reason"],
            "Status": status_str
        })
        
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write("No matching candidates found.")
        
    st.markdown("### View Individual Candidate Output")
    candidate_options = [
        f"#{r['candidate_number']} - {r['name']} ({r['file_name']})"
        for r in filtered_results
    ]
    
    if candidate_options:
        selected_option = st.selectbox("Select a candidate to view details", options=candidate_options)
        selected_idx = candidate_options.index(selected_option)
        selected_cand = filtered_results[selected_idx]
        
        if selected_cand["success"] and selected_cand["result"]:
            res_val = selected_cand["result"]
            
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "1. Canonical Profile",
                "2. Projected Output",
                "3. Provenance",
                "4. Confidence Scores",
                "5. Processing Logs"
            ])
            
            with tab1:
                st.markdown("#### Unified Canonical Profile")
                st.json(res_val["canonical_profile"])
                
            with tab2:
                st.markdown("#### Projected & Reshaped Output")
                st.json(res_val["projected_output"])
                
                projected_json_str = json.dumps(res_val["projected_output"], indent=2)
                st.download_button(
                    label=f"Download Projected JSON for {selected_cand['name']}",
                    data=projected_json_str,
                    file_name=f"candidate_{selected_cand['candidate_number']}_{selected_cand['name'].replace(' ', '_')}.json",
                    mime="application/json",
                    key=f"dl_{selected_cand['candidate_number']}"
                )
                
            with tab3:
                st.markdown("#### Data Provenance Tracker")
                prov_list = res_val["provenance"]
                if prov_list:
                    df_prov = pd.DataFrame(prov_list)
                    st.dataframe(df_prov, use_container_width=True)
                else:
                    st.write("Provenance tracking is disabled or empty.")
                    
            with tab4:
                st.markdown("#### Field Confidence & Match Statistics")
                c_col1, c_col2 = st.columns([1, 2])
                
                with c_col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Overall Profile Confidence</div>
                        <div class="metric-value">{res_val['overall_confidence'] * 100:.1f}%</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    match_info = res_val["match_result"]
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">Source Match Score</div>
                        <div class="metric-value">{match_info['score'] * 100:.0f}%</div>
                        <div style="font-size:0.85rem; color:#64748B; margin-top:0.5rem;">
                            Matched via: <b>{match_info['reason'].replace('_', ' ')}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c_col2:
                    st.markdown("##### Individual Field Confidence Scores")
                    df_conf = pd.DataFrame(
                        list(res_val["confidence_scores"].items()),
                        columns=["Profile Field", "Confidence Score"]
                    )
                    st.dataframe(df_conf, use_container_width=True)
                    
            with tab5:
                st.markdown("#### Pipeline Runtime Execution Log")
                st.code(res_val["logs"], language="log")
        else:
            st.error(f"Candidate process failed: {selected_cand.get('error', 'Unknown Error')}")
            if selected_cand.get("result") and "logs" in selected_cand["result"]:
                with st.expander("Show Execution Logs"):
                    st.code(selected_cand["result"]["logs"], language="log")
else:
    st.info("💡 Please specify both a Structured Source and an Unstructured Source (file upload or profile URL) to enable transformation.")
