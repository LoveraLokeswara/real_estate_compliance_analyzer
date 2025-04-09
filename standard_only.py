import os
import fitz  # PyMuPDF for PDF handling
import pandas as pd
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
MODEL = "anthropic/claude-3-sonnet"  # Model to be used for API calls

# Function to extract text from a PDF file
def extract_pdf_text(file_content):
    doc = fitz.open(stream=file_content, filetype="pdf")  # Open the PDF file
    text = ""
    for page in doc:  # Iterate through each page
        text += page.get_text()  # Extract text from the page
    return text.lower().replace("\n", " ").replace("  ", " ")  # Clean up the text

# Function to call the Claude AI agent with a prompt
def call_agent(prompt, model=MODEL, api_key=None):
    if api_key is None:
        api_key = OPENROUTER_API_KEY
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapplication.com/",  # Update with your application's URL
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
        error_message = f"Error: {response.status_code}, {response.text}"
        print(error_message)  # Log error
        return error_message

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

def analyze_real_estate_document(pdf_file_content, checklist_file_content, prompts_dir=None, api_key=None):
    """
    Analyze a real estate document against a compliance checklist and provide only standard report
    
    Args:
        pdf_file_content (bytes): Content of the PDF file to analyze
        checklist_file_content (bytes): Content of the Excel checklist file
        prompts_dir (str, optional): Directory containing prompt files. Defaults to None.
        api_key (str, optional): API key for OpenRouter. Defaults to environment variable.
        
    Returns:
        dict: A dictionary containing:
            - standard_report (str): The standard analysis report
            - standard_pdf (BytesIO): PDF version of the standard report
            - timestamp (str): Timestamp when the analysis was performed
    """
    try:
        # Extract text from the uploaded PDF
        pdf_text = extract_pdf_text(pdf_file_content)
        
        # Read the checklist from the Excel file
        checklist_buffer = BytesIO(checklist_file_content)
        checklist = pd.read_excel(checklist_buffer)
        
        results = []  # List to hold analysis results
        for index, row in checklist.iterrows():  # Iterate through each row in the checklist
            clause_id = row["Code form."]  # Get clause ID
            clause_name = row["Nom de la clause"]  # Get clause name
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
        
        # Corrected from original code - don't overwrite the analysis with pdf_text
        # standard_analysis = pdf_text  # This was a bug in the original code

        # Prompts for AI analysis
        if prompts_dir:
            std_prompt_file_path = os.path.join(prompts_dir, "standard_prompt.txt")
            
            with open(std_prompt_file_path, "r") as f:
                std_prompt = f.read()  # Read the standard prompt
        else:
            # Default prompt if path not provided
            std_prompt = "Please analyze this real estate document for compliance with the provided checklist."

        # Prepare prompt for the AI
        standard_prompt = std_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using:{checklist}"""

        # Call the AI agent for standard report only
        standard_report = call_agent(standard_prompt, api_key=api_key)  # Get standard report
        
        # Generate PDF
        standard_pdf = text_to_pdf(standard_report)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            "standard_report": standard_report,
            "standard_pdf": standard_pdf,
            "timestamp": timestamp
        }
        
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return {
            "error": str(e),
            "standard_report": None,
            "standard_pdf": None,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        }

# Example usage:
if __name__ == "__main__":
    # This is just for testing/demonstration purposes
    with open("form-dv-test-2.pdf", "rb") as pdf_file, open("formulaires-analyse-vt (DV).xlsx", "rb") as excel_file:
        pdf_content = pdf_file.read()
        excel_content = excel_file.read()
        
        results = analyze_real_estate_document(
            pdf_content, 
            excel_content,
            prompts_dir="/Users/a1/Documents/GitHub/real_estate_compliance_analyzer/"
        )
        
        if "error" in results:
            print(f"Analysis failed: {results['error']}")
        else:
            print("Analysis completed successfully")
            print(f"Standard Report Length: {len(results['standard_report'])}")
            
            # Save PDF for testing
            with open(f"standard_report_{results['timestamp']}.pdf", "wb") as f:
                f.write(results['standard_pdf'].getvalue())