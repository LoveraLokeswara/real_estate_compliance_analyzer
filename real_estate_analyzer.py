import os
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import requests
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime

# Load API key
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-3-sonnet"

# Extract PDF text
def extract_pdf_text(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text.lower().replace("\n", " ").replace("  ", " ")

# Claude call
def call_agent(prompt, model=MODEL):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501/", 
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload)
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        st.error(f"Error: {response.status_code}, {response.text}")
        return f"Error: {response.status_code}, {response.text}"

# Text to PDF (reportlab)
def text_to_pdf(text, max_width=170*mm):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x_margin, y_margin = 20*mm, 20*mm
    y = height - y_margin
    c.setFont("Helvetica", 11)

    def wrap_line(line, font_name="Helvetica", font_size=11):
        words = line.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if stringWidth(test_line, font_name, font_size) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    for raw_line in text.split("\n"):
        wrapped_lines = wrap_line(raw_line)
        for line in wrapped_lines:
            if y < y_margin:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = height - y_margin
            c.drawString(x_margin, y, line)
            y -= 14

    c.save()
    buffer.seek(0)
    return buffer

# Streamlit App
st.set_page_config(page_title="Document Analysis System", page_icon="📄", layout="wide")
st.title("📋 Real Estate Compliance Analyzer")
st.markdown("Upload a document to analyze and a validation table for reference")

col1, col2 = st.columns(2)
with col1:
    uploaded_form = st.file_uploader("Upload completed PDF form", type=["pdf"])
with col2:
    uploaded_checklist = st.file_uploader("Upload checklist Excel file", type=["xlsx"])

if uploaded_form and uploaded_checklist:
    if st.button("🧠 Analyze"):
        with st.spinner("Analyzing document..."):
            pdf_text = extract_pdf_text(uploaded_form)
            checklist = pd.read_excel(uploaded_checklist)

            results = []
            for index, row in checklist.iterrows():
                clause_id = row["Code form."]
                clause_name = row["Nom de la clause"]
                validations = str(row["Éléments de validation"])

                status = "✅ Conforme"
                missing = []

                for point in validations.split("-"):
                    point = point.strip().lower()
                    if point and point not in pdf_text:
                        status = "🟡 Partiellement conforme"
                        missing.append(point)

                if any("rapport" in m for m in missing):
                    status = "🔴 Non conforme"

                results.append(f"### {clause_id} - {clause_name}\nStatus: {status}\nMissing: {', '.join(missing) if missing else 'None'}\n")

            standard_analysis = "".join(results)
            standard_analysis = pdf_text

            # Prompts
            script_dir = os.path.dirname(os.path.abspath(__file__))
            std_prompt_file_path = os.path.join(script_dir, "standard_prompt.txt")
            spec_prompt_file_path = os.path.join(script_dir, "specialized_prompt.txt")

            with open(std_prompt_file_path, "r") as f:
                std_prompt = f.read()
            with open(std_prompt_file_path, "r") as f:
                spec_prompt = f.read()

            specialized_prompt = spec_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using: {checklist}"""

            standard_prompt = std_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using:{checklist}"""

            # Claude reports
            standard_report = call_agent(standard_prompt)
            specialized_report = call_agent(specialized_prompt)

            # Store in session
            st.session_state["standard_report"] = standard_report
            st.session_state["specialized_report"] = specialized_report
            st.session_state["reports_generated"] = True

        st.success("✅ Analysis complete!")

# Show download buttons if analysis is done
if st.session_state.get("reports_generated"):
    tab1, tab2 = st.tabs(["Standard Analysis", "Specialized Analysis"])
    with tab1:
        if st.session_state["standard_report"]:
            st.markdown("## Standard Analysis Results")
            st.markdown(st.session_state["standard_report"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            std_pdf = text_to_pdf(st.session_state["standard_report"])
            st.download_button("📥 Download Standard Analysis (PDF)", data=std_pdf, file_name="standard_analysis.pdf", mime="application/pdf")
        else:
            st.info("Click 'Generate Standard Analysis' to view results here.")

    # Display specialized analysis results
    with tab2:
        if st.session_state["specialized_report"]:
            st.markdown("## Specialized Analysis Results")
            st.markdown(st.session_state["specialized_report"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            spec_pdf = text_to_pdf(st.session_state["specialized_report"])
            st.download_button("📥 Download Specialized Analysis (PDF)", data=spec_pdf, file_name="specialized_analysis.pdf", mime="application/pdf")
        else:
            st.info("Click 'Generate Specialized Analysis' to view results here.")


    # std_pdf = text_to_pdf(st.session_state["standard_report"])
    # spec_pdf = text_to_pdf(st.session_state["specialized_report"])

    # st.download_button("📥 Download Standard Analysis (PDF)", data=std_pdf, file_name="standard_analysis.pdf", mime="application/pdf")
    # st.download_button("📥 Download Specialized Analysis (PDF)", data=spec_pdf, file_name="specialized_analysis.pdf", mime="application/pdf")
