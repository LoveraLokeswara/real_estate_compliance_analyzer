import os
import fitz  # PyMuPDF for PDF handling
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import requests
import json
import re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
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
def call_agent(prompt, model=MODEL, temperature=0.2):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501/",  # Referer for the request
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2  # Add temperature parameter to control randomness
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
    buffer = BytesIO()  # Create a buffer to hold the PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, 
                           topMargin=20*mm, bottomMargin=20*mm)
    
    # Create styles
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    heading1_style = styles["Heading1"]
    heading2_style = styles["Heading2"]
    heading3_style = styles["Heading3"]
    
    # Create a style for table cells
    table_style = ParagraphStyle(
        'TableStyle',
        parent=normal_style,
        fontSize=9,
        leading=12
    )
    
    # Story will contain all elements to be added to the document
    story = []
    
    # Helper function to detect if a line is part of a table
    def is_table_row(line):
        # Match any line that starts and ends with | and has at least one | in the middle
        return bool(re.match(r'^\s*\|.*\|.*\|\s*$', line))
    
    # Helper function to detect if a line is a table separator
    def is_table_separator(line):
        return bool(re.match(r'^\s*\|\s*[-:]+\s*\|.*\|\s*$', line))
    
    # Helper function to clean text and replace HTML entities
    def clean_text(text):
        # Replace common HTML entities
        replacements = {
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&apos;': "'",
            '&ndash;': '–',
            '&mdash;': '—'
        }
        
        for entity, replacement in replacements.items():
            text = text.replace(entity, replacement)
            
        return text
    
    # Pre-process the text to detect and format tables
    # This helps with handling tables that might not be in standard Markdown format
    def preprocess_text(text):
        lines = text.split('\n')
        processed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Special handling for non-standard tables (no separator row)
            # For example: | Section | Détails conformes |
            if line.startswith('|') and line.endswith('|') and '|' in line[1:-1]:
                # Check if this might be the start of a table without proper markdown formatting
                table_lines = []
                table_lines.append(line)
                
                # Look ahead to see if there are more lines that look like table rows
                j = i + 1
                while j < len(lines) and lines[j].strip().startswith('|') and lines[j].strip().endswith('|'):
                    table_lines.append(lines[j].strip())
                    j += 1
                
                # If we have what looks like a table (at least 2 rows)
                if len(table_lines) >= 2:
                    # For tables without a separator row, insert one
                    first_row = table_lines[0]
                    col_count = first_row.count('|') - 1
                    separator_row = '|' + '|'.join([' --- ' for _ in range(col_count)]) + '|'
                    
                    # Add the first row
                    processed_lines.append(table_lines[0])
                    # Add our constructed separator
                    processed_lines.append(separator_row)
                    # Add the rest of the rows
                    for table_line in table_lines[1:]:
                        processed_lines.append(table_line)
                    
                    i = j - 1  # Skip to after the table (-1 because we'll increment i at the end of the loop)
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)
            
            i += 1
        
        return '\n'.join(processed_lines)
    
    # Preprocess the text to handle non-standard tables
    text = preprocess_text(text)
    
    # Process the text line by line
    lines = text.split('\n')
    i = 0
    
    while i < len(lines):
        line = clean_text(lines[i])
        
        # Check for Markdown headings
        if line.startswith('# '):
            story.append(Paragraph(line[2:], heading1_style))
            story.append(Spacer(1, 10))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], heading2_style))
            story.append(Spacer(1, 8))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], heading3_style))
            story.append(Spacer(1, 6))
        # Check for table
        elif is_table_row(line):
            # We found a table, collect all table rows
            table_lines = []
            table_lines.append(line)  # Add first row
            
            # Continue collecting table rows until we hit a non-table row
            while i + 1 < len(lines) and is_table_row(lines[i + 1]):
                i += 1
                table_lines.append(lines[i])
            
            # Process the table
            table_data = []
            has_header = False
            
            for idx, table_line in enumerate(table_lines):
                if is_table_separator(table_line):  # Found a separator line
                    has_header = True
                    continue  # Skip the separator line
                
                # Split by '|', remove the first and last empty parts, and strip whitespace
                cells = [cell.strip() for cell in table_line.split('|')[1:-1]]
                # Convert each cell to a Paragraph for better text handling
                row = [Paragraph(cell, table_style) for cell in cells]
                table_data.append(row)
            
            # Create a ReportLab table
            if table_data:
                # Calculate the available width
                available_width = doc.width
                
                # Calculate column widths based on content
                # For simplicity, we'll distribute the width equally
                col_count = len(table_data[0])
                col_width = available_width / col_count
                
                # Create the table with specified column widths
                col_widths = [col_width] * col_count
                table = Table(table_data, colWidths=col_widths)
                
                # Style the table
                table_style_commands = [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ]
                
                if has_header or len(table_data) > 1:
                    # Style the header row if we have one or if there are multiple rows
                    table_style_commands.extend([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ])
                
                # Add alternating row colors for better readability
                for row in range(1, len(table_data)):
                    if row % 2 == 0:
                        table_style_commands.append(('BACKGROUND', (0, row), (-1, row), colors.whitesmoke))
                
                table.setStyle(TableStyle(table_style_commands))
                story.append(table)
                story.append(Spacer(1, 12))
        else:
            # Regular paragraph text
            if line.strip():  # Only add non-empty lines
                story.append(Paragraph(line, normal_style))
                story.append(Spacer(1, 6))
            
        i += 1
    
    # Build the PDF document
    doc.build(story)
    
    buffer.seek(0)  # Move to the beginning of the buffer
    return buffer    # Return the buffer containing the PDF

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
            # specialized_prompt = spec_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using: {checklist}"""
            standard_prompt = std_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using:{checklist}. Make sure to check if the document fulfil all the required clauses of the checklist. Analyze the document thoroughly."""

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
    # tab1, tab2 = st.tabs(["Standard Analysis", "Specialized Analysis"])  # Create tabs for reports
    # with tab1:
    if st.session_state["standard_report"]:
        st.markdown("## Standard Analysis Results")                 # Display standard analysis results
        st.markdown(st.session_state["standard_report"])            # Show the report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")        # Generate timestamp for file naming
        std_pdf = text_to_pdf(st.session_state["standard_report"])  # Convert report to PDF
        st.download_button("📥 Download Standard Analysis (PDF)", data=std_pdf, file_name="standard_analysis.pdf", mime="application/pdf")  # Download button
    else:
        st.info("Click 'Generate Standard Analysis' to view results here.")  # Info message if no report

    # Display specialized analysis results
    # with tab2:
    #     if st.session_state["specialized_report"]:
    #         st.markdown("## Specialized Analysis Results")                  # Display specialized analysis results
    #         st.markdown(st.session_state["specialized_report"])             # Show the report
    #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")            # Generate timestamp for file naming
    #         spec_pdf = text_to_pdf(st.session_state["specialized_report"])  # Convert report to PDF
    #         st.download_button("📥 Download Specialized Analysis (PDF)", data=spec_pdf, file_name="specialized_analysis.pdf", mime="application/pdf")  # Download button
    #     else:
    #         st.info("Click 'Generate Specialized Analysis' to view results here.")   # Info message if no report


    # std_pdf = text_to_pdf(st.session_state["standard_report"])
    # spec_pdf = text_to_pdf(st.session_state["specialized_report"])

    # st.download_button("📥 Download Standard Analysis (PDF)", data=std_pdf, file_name="standard_analysis.pdf", mime="application/pdf")
    # st.download_button("📥 Download Specialized Analysis (PDF)", data=spec_pdf, file_name="specialized_analysis.pdf", mime="application/pdf")
