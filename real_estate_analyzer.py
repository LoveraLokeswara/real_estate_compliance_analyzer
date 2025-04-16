import os
import fitz  # PyMuPDF for PDF handling
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

# Load API key from environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "anthropic/claude-3.5-sonnet"  # Model to be used for API calls

# Function to extract text from a PDF file
def extract_pdf_text(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")  # Open the PDF file
    text = ""
    for page in doc:  # Iterate through each page
        text += page.get_text()  # Extract text from the page
    return text.lower().replace("\n", " ").replace("  ", " ")  # Clean up the text

# Function to call the Claude AI agent with a prompt
def call_agent(prompt, model=MODEL):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501/",  # Referer for the request
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }

    # Make a POST request to the AI API
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload)  # Convert payload to JSON
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]  # Return the AI's response
    else:
        st.error(f"Error: {response.status_code}, {response.text}")  # Handle errors
        return f"Error: {response.status_code}, {response.text}"

# Function to convert text to a PDF using ReportLab
def text_to_pdf(text, max_width=170*mm):
    buffer = BytesIO()                      # Create a buffer to hold the PDF
    c = canvas.Canvas(buffer, pagesize=A4)  # Create a canvas for the PDF
    width, height = A4                      # Get the dimensions of the A4 page
    x_margin, y_margin = 20*mm, 20*mm       # Set margins
    y = height - y_margin                   # Start drawing from the top
    c.setFont("Helvetica", 11)              # Set the font for the PDF

    # Function to wrap lines of text to fit within the specified width
    def wrap_line(line, font_name="Helvetica", font_size=11):
        words = line.split()  # Split the line into words
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()  # Test the current line with the new word
            if stringWidth(test_line, font_name, font_size) <= max_width:
                current_line = test_line  # If it fits, add the word to the current line
            else:
                lines.append(current_line)  # If it doesn't fit, save the current line
                current_line = word  # Start a new line with the current word
        if current_line:
            lines.append(current_line)  # Add the last line if it exists
        return lines

    # Iterate through each line of the text
    for raw_line in text.split("\n"):
        wrapped_lines = wrap_line(raw_line)  # Wrap the line to fit the page
        for line in wrapped_lines:
            if y < y_margin:                    # Check if we need to start a new page
                c.showPage()                    # Create a new page
                c.setFont("Helvetica", 11)      # Reset the font
                y = height - y_margin           # Reset the y position
            c.drawString(x_margin, y, line)     # Draw the line on the PDF
            y -= 14                             # Move down for the next line

    c.save()        # Save the PDF to the buffer
    buffer.seek(0)  # Move to the beginning of the buffer
    return buffer   # Return the buffer containing the PDF

# Streamlit App configuration
st.set_page_config(page_title="Document Analysis System", page_icon="📄", layout="wide")
st.title("📋 Real Estate Compliance Analyzer")
st.markdown("Upload a document to analyze and a validation table for reference")

col1, col2 = st.columns(2)
with col1:
    uploaded_form = st.file_uploader("Upload completed PDF form", type=["pdf"])  # PDF upload
with col2:
    uploaded_checklist = st.file_uploader("Upload checklist Excel file", type=["xlsx"])  # Excel upload

if uploaded_form and uploaded_checklist:
    if st.button("🧠 Analyze"):
        with st.spinner("Analyzing document..."):           # Show a spinner while analyzing
            pdf_text = extract_pdf_text(uploaded_form)      # Extract text from the uploaded PDF
            checklist = pd.read_excel(uploaded_checklist)   # Read the checklist from the Excel file

            results = []                                    # List to hold analysis results of the pdf with respect to the checklist
            for index, row in checklist.iterrows():         # Iterate through each row in the checklist
                clause_id = row["Code form."]               # Get clause ID
                clause_name = row["Nom de la clause"]       # Get clause name
                validations = str(row["Éléments de validation"])  # Get validation elements

                status = "✅ Conforme"  # Default status
                missing = []  # List to hold missing items

                for point in validations.split("-"):  # Check each validation point
                    point = point.strip().lower()  # Clean up the point
                    if point and point not in pdf_text:  # Check if the point is missing in the PDF text
                        status = "🟡 Partiellement conforme"  # Update status if partially compliant
                        missing.append(point)  # Add missing point to the list

                if any("rapport" in m for m in missing):  # Check for specific missing items
                    status = "🔴 Non conforme"  # Update status if non-compliant

                # Append the result for this clause
                results.append(f"### {clause_id} - {clause_name}\nStatus: {status}\nMissing: {', '.join(missing) if missing else 'None'}\n")

            standard_analysis = "".join(results)  # Combine results into a single string
            standard_analysis = pdf_text  # (This line seems to overwrite the analysis results)

            # Prompts for AI analysis
            script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the script directory
            std_prompt_file_path = os.path.join(script_dir, "standard_prompt.txt")  # Path for standard prompt
            spec_prompt_file_path = os.path.join(script_dir, "specialized_prompt.txt")  # Path for specialized prompt

            with open(std_prompt_file_path, "r") as f:
                std_prompt = f.read()  # Read the standard prompt
            with open(std_prompt_file_path, "r") as f:
                spec_prompt = f.read()  # Read the specialized prompt

            # Prepare prompts for the AI
            specialized_prompt = spec_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using: {checklist}"""
            standard_prompt = std_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using:{checklist}"""

            # Call the AI agent for reports
            standard_report = call_agent(standard_prompt)  # Get standard report
            # specialized_report = call_agent(specialized_prompt)  # Get specialized report

            # Store reports in session state
            st.session_state["standard_report"] = standard_report
            # st.session_state["specialized_report"] = specialized_report
            st.session_state["reports_generated"] = True  # Mark reports as generated

        st.success("✅ Analysis complete!")  # Notify user of completion

# Show download buttons if analysis is done
if st.session_state.get("reports_generated"):
    tab1, tab2 = st.tabs(["Standard Analysis", "Specialized Analysis"])  # Create tabs for reports
    with tab1:
        if st.session_state["standard_report"]:
            st.markdown("## Standard Analysis Results")                 # Display standard analysis results
            st.markdown(st.session_state["standard_report"])            # Show the report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")        # Generate timestamp for file naming
            std_pdf = text_to_pdf(st.session_state["standard_report"])  # Convert report to PDF
            st.download_button("📥 Download Standard Analysis (PDF)", data=std_pdf, file_name="standard_analysis.pdf", mime="application/pdf")  # Download button
        else:
            st.info("Click 'Generate Standard Analysis' to view results here.")  # Info message if no report

    # Display specialized analysis results
    with tab2:
        if st.session_state["specialized_report"]:
            st.markdown("## Specialized Analysis Results")                  # Display specialized analysis results
            st.markdown(st.session_state["specialized_report"])             # Show the report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")            # Generate timestamp for file naming
            spec_pdf = text_to_pdf(st.session_state["specialized_report"])  # Convert report to PDF
            st.download_button("📥 Download Specialized Analysis (PDF)", data=spec_pdf, file_name="specialized_analysis.pdf", mime="application/pdf")  # Download button
        else:
            st.info("Click 'Generate Specialized Analysis' to view results here.")   # Info message if no report


    # std_pdf = text_to_pdf(st.session_state["standard_report"])
    # spec_pdf = text_to_pdf(st.session_state["specialized_report"])

    # st.download_button("📥 Download Standard Analysis (PDF)", data=std_pdf, file_name="standard_analysis.pdf", mime="application/pdf")
    # st.download_button("📥 Download Specialized Analysis (PDF)", data=spec_pdf, file_name="specialized_analysis.pdf", mime="application/pdf")
