import streamlit as st
import google.generativeai as genai
import os
import tempfile
import time

# ==========================================
# ⚙️ DOCTOR'S PREFERENCES (EDIT THIS SECTION)
# ==========================================
# Edit these variables to "Save" your training permanently.
# This prevents you from having to type them every time you open the app.

DEFAULT_DOCTOR_NAME = "Dr. [Your Name]"
DEFAULT_SPECIALTY = "General Practice / OPD"

# Your preferred structure (The AI will stick to this)
DEFAULT_FORMAT_INSTRUCTIONS = """
1. Chief Complaints (C/O) - with duration
2. History of Presenting Illness (HOPI) - Chronological order, Bullet points
3. Relevant Past History (Medical/Surgical)
4. Vitals (if mentioned)
5. Provisional Diagnosis
6. Plan / Medications
"""

# Your abbreviation rules
DEFAULT_ABBREVIATIONS = "Use standard abbreviations (T2DM, HTN, CVD). Write 'od'/'bd' for dosages."

# One-Shot Training Example (The most powerful way to train)
# Paste a sanitized example of a "Perfect Case Sheet" here. The AI will copy this style.
DEFAULT_EXAMPLE_CASE = """
C/O:
- Fever x 3 days
- Cough with expectoration x 2 days

HOPI:
- Patient developed high grade fever 3 days back. 
- Associated with generalized body pain.
- Cough started 2 days back, productive in nature, yellowish sputum.
- No h/o breathlessness or chest pain.
- No h/o similar illness in recent past.

Past Hx:
- K/c/o T2DM on OHA (Metformin).
- No drug allergies.

Rx:
- T. Paracetamol 650mg t.i.d x 3 days
- Warm saline gargle
"""

# ==========================================
# 🚀 MAIN APPLICATION CODE
# ==========================================

st.set_page_config(
    page_title="Tanglish Clinical Scribe",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Management ---
if "case_sheet" not in st.session_state:
    st.session_state.case_sheet = ""

def process_consultation(api_key, audio_file, style_guide):
    """Sends audio to Gemini and retrieves the structured case sheet."""
    try:
        genai.configure(api_key=api_key)
        
        # 1. Upload File
        with st.spinner("📤 Uploading audio to secure analysis engine..."):
            # Create a temp file because Gemini needs a file path
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            
            myfile = genai.upload_file(tmp_path)
        
        # 2. Wait for processing (Gemini sometimes needs a moment for audio)
        while myfile.state.name == "PROCESSING":
            time.sleep(1)
            myfile = genai.get_file(myfile.name)

        # 3. Generate Content
        with st.spinner("🧠 Analyzing conversation & Formatting (Tanglish -> English)..."):
            model = genai.GenerativeModel("gemini-1.5-flash-latest")
            
            # The Mega-Prompt
            prompt = f"""
            Role: You are an expert Medical Scribe assisting {style_guide['name']} in an Indian {style_guide['specialty']} OPD.
            
            Task: Listen to the audio (mixed Tamil/English) and generate a clinical case sheet.
            
            CRITICAL RULES:
            1. **Translation:** Accurately translate Tamil medical descriptions to standard English medical terminology (e.g., "Nenju erichal" -> "Retrosternal burning sensation/Heartburn").
            2. **Filtering:** Completely ignore small talk, greetings, or irrelevant personal chatter.
            3. **Inference:** If the doctor asks "Sugar irukka?", infer they are asking about Diabetes Mellitus status.
            
            FORMATTING REQUIREMENTS:
            {style_guide['format']}
            
            ABBREVIATION STYLE:
            {style_guide['abbr']}
            
            STYLE REFERENCE (MIMIC THIS WRITING STYLE):
            {style_guide['example']}
            """
            
            response = model.generate_content([myfile, prompt])
            
            # Cleanup
            os.remove(tmp_path)
            
            return response.text

    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- SIDEBAR UI ---
with st.sidebar:
    st.title("🩺 Scribe Settings")
    
    # API Key Handling
    # Tip: In the future, we can hide this using Streamlit Secrets for auto-login
    api_key = st.text_input("🔑 Google API Key", type="password", help="Get this from aistudio.google.com")
    
    st.divider()
    
    st.subheader("👨‍🏫 Training Module")
    with st.expander("Edit Style & Preferences", expanded=False):
        doc_name = st.text_input("Doctor Name", DEFAULT_DOCTOR_NAME)
        specialty = st.text_input("Specialty", DEFAULT_SPECIALTY)
        format_instr = st.text_area("Format Instructions", DEFAULT_FORMAT_INSTRUCTIONS, height=150)
        abbr_instr = st.text_input("Abbreviation Style", DEFAULT_ABBREVIATIONS)
        example_case = st.text_area("Style Example (The AI will mimic this)", DEFAULT_EXAMPLE_CASE, height=200)

# --- MAIN PAGE UI ---
st.title("🎙️ AI OPD Scribe (Tanglish)")
st.markdown(f"**Current Profile:** {doc_name} | **Mode:** Active Listening")

# Audio Input Widget (Native Streamlit)
audio_val = st.audio_input("🔴 Press Microphone to Start Consultation")

if audio_val:
    if not api_key:
        st.warning("⚠️ Please enter your API Key in the sidebar to proceed.")
    else:
        # Bundle the settings
        style_settings = {
            "name": doc_name,
            "specialty": specialty,
            "format": format_instr,
            "abbr": abbr_instr,
            "example": example_case
        }
        
        # Run the magic
        result = process_consultation(api_key, audio_val, style_settings)
        
        if result:
            st.session_state.case_sheet = result

# --- RESULTS DISPLAY ---
if st.session_state.case_sheet:
    st.divider()
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Generated Case Sheet")
        # Text area allows you to edit quickly before copying
        final_text = st.text_area("Review & Edit", st.session_state.case_sheet, height=500)
    
    with col2:
        st.subheader("Actions")
        st.info("💡 Review the notes for accuracy.")
        
        # Copy Helper
        st.write("Click corner icon to copy 👇")
        st.code(final_text, language="markdown")
        
        # Reset Button
        if st.button("Start New Patient"):
            st.session_state.case_sheet = ""
            st.rerun()

# --- FOOTER ---
st.markdown("---")

st.caption("🔒 Privacy Note: Audio is processed temporarily by Google Gemini and deleted immediately. No data is stored on this server.")
