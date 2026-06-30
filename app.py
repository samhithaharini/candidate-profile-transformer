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
    
    /* Uploaded file name text color visibility */
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"],
    [data-testid="stFileUploader"] div,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stUploadedFile"],
    [data-testid="stUploadedFile"] div,
    [data-testid="stUploadedFile"] span,
    [data-testid="stUploadedFile"] p {
        color: #1E3A8A !important;
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
    div.stButton > button:first-child {
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
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(30, 58, 138, 0.35);
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
    st.markdown(f"### Section 1: Upload Structured Source ({structured_format})")
    struct_file = st.file_uploader(
        f"Upload {structured_format} File",
        type=["csv", "json"] if struct_type == "ats_json" else ["csv"],
        key="struct_file_uploader"
    )
    if not struct_file and load_sample and struct_type == "csv":
        st.info("ℹ️ Using sample structured source: `sample_data/recruiter.csv` (Jane Doe)")

with col2:
    st.markdown(f"### Section 2: Upload Unstructured Source ({unstructured_format})")
    
    unstruct_file = None
    unstruct_url = ""
    url_valid = True
    
    if unstruct_type == "resume_pdf":
        unstruct_file = st.file_uploader(
            "Upload Resume PDF",
            type=["pdf"],
            key="unstruct_file_uploader"
        )
    elif unstruct_type == "recruiter_notes":
        unstruct_file = st.file_uploader(
            "Upload Recruiter Notes TXT",
            type=["txt"],
            key="unstruct_file_uploader"
        )
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
        unstruct_file = st.file_uploader(
            "Alternative: Upload LinkedIn JSON File",
            type=["json"],
            key="unstruct_file_uploader"
        )
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
        unstruct_file = st.file_uploader(
            "Alternative: Upload GitHub JSON File",
            type=["json"],
            key="unstruct_file_uploader"
        )

# Resolve paths and names for Structured Source
struct_path = None
struct_loaded = False
struct_file_name = ""
struct_file_size = 0

if struct_file:
    struct_path = save_uploaded_file(struct_file)
    struct_loaded = True
    struct_file_name = struct_file.name
    struct_file_size = struct_file.size
elif load_sample and struct_type == "csv":
    struct_path = Path("sample_data/recruiter.csv")
    struct_loaded = True
    struct_file_name = "recruiter.csv"
    struct_file_size = struct_path.stat().st_size

# Resolve paths and names for Unstructured Source
unstruct_path = None
unstruct_loaded = False
unstruct_file_name = ""
unstruct_file_size = 0

if unstruct_file:
    unstruct_path = save_uploaded_file(unstruct_file)
    unstruct_loaded = True
    unstruct_file_name = unstruct_file.name
    unstruct_file_size = unstruct_file.size
else:
    if unstruct_type in ("linkedin_profile", "github_profile"):
        unstruct_loaded = bool(unstruct_url and url_valid)
    elif load_sample:
        if unstruct_type == "resume_pdf":
            unstruct_path = Path("sample_data/resume.pdf")
            unstruct_loaded = True
            unstruct_file_name = "resume.pdf"
            unstruct_file_size = unstruct_path.stat().st_size
        elif unstruct_type == "recruiter_notes":
            unstruct_path = Path("sample_data/recruiter_notes.txt")
            unstruct_loaded = True
            unstruct_file_name = "recruiter_notes.txt"
            unstruct_file_size = unstruct_path.stat().st_size

st.markdown("---")

# --- SECTION 3 & 4: DETECTED TYPES & PREVIEWS ---
if struct_loaded or unstruct_loaded:
    st.markdown("### Files Analysis Panel")
    preview_cols = st.columns(2)
    
    with preview_cols[0]:
        if struct_loaded and struct_path:
            if struct_file:
                st.info(f"📁 **Structured Source Detected**: `{struct_file_name}` ({struct_file_size / 1024:.2f} KB)")
            else:
                st.info(f"📁 **Structured Source (Sample)**: `{struct_file_name}` ({struct_file_size / 1024:.2f} KB)")
            st.markdown("#### Preview Extracted Structured Entities")
            
            if struct_file:
                temp_path = save_uploaded_file(struct_file)
                preview_data = parse_and_preview(temp_path, struct_type)
                temp_path.unlink()
            else:
                preview_data = parse_and_preview(struct_path, struct_type)
            
            if preview_data:
                st.json(preview_data)
        else:
            st.warning("⚠️ Structured source not uploaded yet.")
            
    with preview_cols[1]:
        if unstruct_type in ("linkedin_profile", "github_profile") and not unstruct_file:
            if unstruct_url and url_valid:
                st.info(f"🔗 **Profile URL Detected**: `{unstruct_url}`")
                st.markdown("#### Preview Extracted Unstructured Entities")
                
                try:
                    raw_data = get_adjusted_profile(unstruct_type, unstruct_url, struct_path, struct_type)
                        
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                        temp_file.write(json.dumps(raw_data).encode("utf-8"))
                        temp_path = Path(temp_file.name)
                        
                    preview_data = parse_and_preview(temp_path, unstruct_type)
                    temp_path.unlink()  # Clean up preview temp
                    
                    if preview_data:
                        st.json(preview_data)
                except Exception as e:
                    st.error(f"Error loading preview: {e}")
            else:
                st.warning("⚠️ Unstructured profile URL not provided or invalid.")
        else:
            if unstruct_loaded and unstruct_path:
                if unstruct_file:
                    st.info(f"📄 **Unstructured Source Detected**: `{unstruct_file_name}` ({unstruct_file_size / 1024:.2f} KB)")
                else:
                    st.info(f"📄 **Unstructured Source (Sample)**: `{unstruct_file_name}` ({unstruct_file_size / 1024:.2f} KB)")
                st.markdown("#### Preview Extracted Unstructured Entities")
                
                if unstruct_file:
                    temp_path = save_uploaded_file(unstruct_file)
                    preview_data = parse_and_preview(temp_path, unstruct_type)
                    temp_path.unlink()
                else:
                    preview_data = parse_and_preview(unstruct_path, unstruct_type)
                
                if preview_data:
                    st.json(preview_data)
            else:
                st.warning("⚠️ Unstructured source not uploaded yet.")
            
    st.markdown("---")

# --- SECTION 5: RUN TRANSFORMATION ---
if struct_loaded and unstruct_loaded:
    st.markdown("### Section 5: Execute Transformation Engine")
    
    if st.button("Run Transformation Pipeline"):
        with st.spinner("Executing pipeline layers..."):
            run_struct_path = struct_path
            is_temp_struct = False
            if struct_file:
                run_struct_path = save_uploaded_file(struct_file)
                is_temp_struct = True
                
            run_unstruct_path = unstruct_path
            is_temp_unstruct = False
            
            try:
                if unstruct_type in ("linkedin_profile", "github_profile") and not unstruct_file:
                    raw_data = get_adjusted_profile(unstruct_type, unstruct_url, struct_path, struct_type)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
                        temp_file.write(json.dumps(raw_data).encode("utf-8"))
                        run_unstruct_path = Path(temp_file.name)
                        is_temp_unstruct = True
                else:
                    if unstruct_file:
                        run_unstruct_path = save_uploaded_file(unstruct_file)
                        is_temp_unstruct = True
                
                controller = PipelineController()
                result = controller.run_pipeline(
                    structured_path=run_struct_path,
                    unstructured_path=run_unstruct_path,
                    structured_type=struct_type,
                    unstructured_type=unstruct_type,
                    config=pipeline_config
                )
                
                if is_temp_struct:
                    run_struct_path.unlink()
                if is_temp_unstruct:
                    run_unstruct_path.unlink()
                
                if result["success"]:
                    st.success("🎉 Pipeline executed successfully!")
                    
                    # Setup 5 tabs
                    tab1, tab2, tab3, tab4, tab5 = st.tabs([
                        "1. Canonical Profile",
                        "2. Projected Output",
                        "3. Provenance",
                        "4. Confidence Scores",
                        "5. Processing Logs"
                    ])
                    
                    with tab1:
                        st.markdown("#### Unified Canonical Profile")
                        st.json(result["canonical_profile"])
                        
                    with tab2:
                        st.markdown("#### Projected & Reshaped Output")
                        st.json(result["projected_output"])
                        
                        # Download button
                        projected_json_str = json.dumps(result["projected_output"], indent=2)
                        st.download_button(
                            label="Download Projected Profile JSON",
                            data=projected_json_str,
                            file_name="candidate_profile.json",
                            mime="application/json"
                        )
                        
                    with tab3:
                        st.markdown("#### Data Provenance Tracker")
                        prov_list = result["provenance"]
                        if prov_list:
                            df_prov = pd.DataFrame(prov_list)
                            st.dataframe(df_prov, use_container_width=True)
                        else:
                            st.write("Provenance tracking is disabled or empty.")
                            
                    with tab4:
                        st.markdown("#### Field Confidence & Match Statistics")
                        c_col1, c_col2 = st.columns([1, 2])
                        
                        with c_col1:
                            # Large Overall Confidence Card
                            st.markdown(f"""
                            <div class="metric-card">
                                <div class="metric-title">Overall Profile Confidence</div>
                                <div class="metric-value">{result['overall_confidence'] * 100:.1f}%</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            match_info = result["match_result"]
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
                                list(result["confidence_scores"].items()),
                                columns=["Profile Field", "Confidence Score"]
                            )
                            st.dataframe(df_conf, use_container_width=True)
                            
                    with tab5:
                        st.markdown("#### Pipeline Runtime Execution Log")
                        st.code(result["logs"], language="log")
                        
                else:
                    st.error(f"❌ Transformation Pipeline failed: {result['error']}")
                    with st.expander("Show Execution Logs"):
                        st.code(result["logs"], language="log")
            except Exception as ex:
                st.error(f"❌ Execution failed: {ex}")
else:
    st.info("💡 Please specify both a Structured Source and an Unstructured Source (file upload or profile URL) to enable transformation.")
