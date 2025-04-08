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
        "HTTP-Referer": "http://localhost:8501/",  # Replace with your actual domain
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
            specialized_prompt = f"""
            <Instruction>
            You are an expert real estate assistant specializing in form validation and compliance analysis. Your task is to analyze a "Déclarations du vendeur" (DV) form based on a detailed validation table that outlines expected responses, required documents, and critical checks for each section (DV1 to DV16).
            
            The first pdf document is the report to analyze. The second xlsx document is the validation table/checklist that provides the criteria for analysis.
            
            You must:
            Evaluate conformity of each section (DV1 to DV16) by comparing the form content with the validation table.

            Find also the name of the person who's selling and who's buying the estate in the signature part. 
            
            Identify issues and provide specialized guidance formatted specifically in four key areas:
            1. Recommended Actions - Specific steps to take to resolve issues
            2. HR Tips - Personnel-related suggestions
            3. Warnings - Critical issues that need immediate attention
            4. Required Training - Training needs identified based on errors
            </Instruction>
            
            Format your output in the following specialized format:
            # ANALYSIS REPORT: [form number]
            
            </br>
            ## Document Overview
            - **Vendor(s)**: [Names]
            - **Date**: [Date]
            - **Property Type**: [Type]
            - **Overall Score**: [score]%
            
            </br>
            ## 🎯 RECOMMENDED ACTIONS
            Section: [Section]
            Action Required: [Specific action]
            Priority: [High/Medium/Low]
            Timeline: [Immediate/Within X days]</br>
            </br>
            
            ## 💡 HR TIPS
            Area: [Area]
            Suggestion: [Suggestion]
            Benefit: [Expected benefit]</br>
            </br>
            
            ## ⚠️ WARNINGS
            Risk Level: [Critical/High/Medium]
            Issue: [Issue description]
            Potential Consequences: [Consequences]
            Mitigation: [Mitigation approach]</br>
            </br>
            
            ## 🎓 REQUIRED TRAINING
            Topic: [Training topic]
            Target Personnel: [Who needs training]
            Format: [Format]
            Urgency: [Urgency level]</br>
            </br>
            
            ## Summary Evaluation
            [Brief summary paragraph with overall assessment]
            Analyse:
            {standard_analysis}
            Using:
            {checklist}
            """

            standard_prompt = f"""
            <Instruction>
            You are an expert real estate assistant specializing in form validation and compliance analysis. Your task is to analyze a "Déclarations du vendeur" (DV) form based on a detailed validation table that outlines expected responses, required documents, and critical checks for each section (DV1 to DV16).
            
            The first pdf document is the report to analyze. The second xlsx document is the validation table/checklist that provides the criteria for analysis.
            
            You must:
            Evaluate conformity of each section (DV1 to DV16) by comparing the form content with the validation table.
            
            Identify:
            ✅ Conforming elements (complete, clear, and documented)
            🟡 Partial elements (missing minor info, ambiguous, incomplete)
            🔴 Critical non-conformities (missing required documentation or information that creates risk)
            
            Give a conformity score as a percentage based on overall completeness and correctness.
            </Instruction>
            
            Format your output as follows:
            DV [form number] : [score]% Voici l'évaluation complète du formulaire "Déclarations du vendeur" (DV) de [NOM VENDEUR(S)], daté du [DATE], pour un immeuble résidentiel de moins de 5 logements.
            
            ✅ SCORE DE CONFORMITÉ GÉNÉRAL : [score]% – [niveau de conformité : Conforme, Conforme avec points à bonifier, Non conforme]
            🟢 Résumé de l'état général du document (structure, signatures, etc.).
            
            🟢 ÉLÉMENTS CONFORMES :
            Section
            Détails conformes
            (List each conforming DV section with relevant details.)
            
            🟡 OBSERVATIONS / POINTS À BONIFIER
            Section
            Problème détecté
            Recommandation
            (List each partially conforming section, what's missing, and how to fix it.)
            
            🔴 POINTS À CORRIGER POUR ÉVITER RISQUES :
            Section
            Risque identifié
            Action immédiate
            (List critical issues and what must be corrected.)
            
            📋 RECOMMANDATIONS À L'AGENCE / COURTIER
            (Add specific recommendations for the agency or broker based on observed patterns or recurring mistakes.)
            
            📢 CONCLUSION
            (Summarize if the form is valid, under what conditions, and what documents must be urgently provided.)

            Important Notes for Evaluation:
            Use section D15 for details if "oui" is checked elsewhere.
            Require Annexe G where applicable (for technical/maintenance details).
            Require original or attached documents (e.g. inspection reports, invoices).
            A missing signature or D15 clarification on a critical item may invalidate the form.
            Analyse:
            {standard_analysis}
            Using:
            {checklist}
            """

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
