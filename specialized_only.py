import os
import fitz  # PyMuPDF for PDF handling
import pandas as pd
from dotenv import load_dotenv
import requests
import json
from io import BytesIO
from datetime import datetime
import re

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

# Function to parse the specialized report into JSON format
def parse_specialized_report_to_json(report_text):
    """
    Parse the specialized report into a structured JSON format with summary, 
    recommended_actions, and warnings sections
    
    Args:
        report_text (str): The specialized report text from the AI
        
    Returns:
        dict: A structured dictionary with the parsed content
    """
    result = {
        "summary": "",
        "recommended_actions": [],
        "warnings": []
    }
    
    # Extract document overview and summary
    summary_match = re.search(r'## Summary Evaluation\s*(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
    
    # Extract recommended actions
    actions_section = re.search(r'## RECOMMENDED ACTIONS(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if actions_section:
        actions_text = actions_section.group(1)
        
        # Find all actions
        action_patterns = re.finditer(r'Section: (.*?)Action Required: (.*?)Priority: (.*?)Timeline: (.*?)(?=Section:|$)', 
                                    actions_text, re.DOTALL)
        
        for match in action_patterns:
            action = {
                "section": match.group(1).strip(),
                "action_required": match.group(2).strip(),
                "priority": match.group(3).strip(),
                "timeline": match.group(4).strip()
            }
            result["recommended_actions"].append(action)
    
    # Extract warnings
    warnings_section = re.search(r'## ⚠️ WARNINGS(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if warnings_section:
        warnings_text = warnings_section.group(1)
        
        # Find all warnings
        warning_patterns = re.finditer(r'Risk Level: (.*?)Issue: (.*?)Potential Consequences: (.*?)Mitigation: (.*?)(?=Risk Level:|$)', 
                                     warnings_text, re.DOTALL)
        
        for match in warning_patterns:
            warning = {
                "risk_level": match.group(1).strip(),
                "issue": match.group(2).strip(),
                "potential_consequences": match.group(3).strip(),
                "mitigation": match.group(4).strip()
            }
            result["warnings"].append(warning)
    
    # Add overview information
    overview_section = re.search(r'## Document Overview(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if overview_section:
        overview_text = overview_section.group(1)
        
        # Extract vendor names
        vendor_match = re.search(r'\*\*Vendor\(s\)\*\*: (.*?)(?=-|\n)', overview_text)
        if vendor_match:
            result["vendor"] = vendor_match.group(1).strip()
        
        # Extract date
        date_match = re.search(r'\*\*Date\*\*: (.*?)(?=-|\n)', overview_text)
        if date_match:
            result["date"] = date_match.group(1).strip()
        
        # Extract property type
        property_match = re.search(r'\*\*Property Type\*\*: (.*?)(?=-|\n)', overview_text)
        if property_match:
            result["property_type"] = property_match.group(1).strip()
        
        # Extract overall score
        score_match = re.search(r'\*\*Overall Score\*\*: (.*?)%', overview_text)
        if score_match:
            result["overall_score"] = score_match.group(1).strip()
    
    return result

def analyze_real_estate_document_json(pdf_file_content, checklist_file_content, api_key=None):
    """
    Analyze a real estate document and output only the specialized analysis in JSON format
    
    Args:
        pdf_file_content (bytes): Content of the PDF file to analyze
        checklist_file_content (bytes): Content of the Excel checklist file
        api_key (str, optional): API key for OpenRouter. Defaults to environment variable.
        
    Returns:
        dict: A dictionary containing:
            - json_output (dict): The specialized analysis in JSON format
            - json_file (str): Path to the saved JSON file
            - timestamp (str): Timestamp when the analysis was performed
    """
    try:
        # Extract text from the uploaded PDF
        pdf_text = extract_pdf_text(pdf_file_content)
        
        # Read the checklist from the Excel file
        checklist_buffer = BytesIO(checklist_file_content)
        checklist = pd.read_excel(checklist_buffer)
        
        # Define specialized prompt
        specialized_prompt = """<Instruction> You are an expert real estate assistant specializing in form validation and compliance analysis. Your task is to analyze a "Déclarations du vendeur" (DV) form based on a detailed validation table that outlines expected responses, required documents, and critical checks for each section (DV1 to DV16).  The first pdf document is the report to analyze. The second xlsx document is the validation table/checklist that provides the criteria for analysis.  You must: Evaluate conformity of each section (DV1 to DV16) by comparing the form content with the validation table.  Find also the name of the person who's selling and who's buying the estate in the signature part.   Identify issues and provide specialized guidance formatted specifically in two key areas: 1. Recommended Actions - Specific steps to take to resolve issues 2. Warnings - Critical issues that need immediate attention  </Instruction>  Format your output in the following specialized format: # ANALYSIS REPORT: [form number]  </br> ## Document Overview - **Vendor(s)**: [Names] - **Date**: [Date] - **Property Type**: [Type] - **Overall Score**: [score]%  </br> ## 🎯 RECOMMENDED ACTIONS Section: [Section] Action Required: [Specific action] Priority: [High/Medium/Low] Timeline: [Immediate/Within X days]</br> </br>  ## ⚠️ WARNINGS Risk Level: [Critical/High/Medium] Issue: [Issue description] Potential Consequences: [Consequences] Mitigation: [Mitigation approach]</br> </br>  ## Summary Evaluation [Brief summary paragraph with overall assessment]"""
        
        # Full prompt with analysis data
        full_prompt = specialized_prompt + f"""\n\n Analyse:{pdf_text} \n\n Using: {checklist}"""
        
        # Call the AI agent for specialized report
        specialized_report = call_agent(full_prompt, api_key=api_key)
        
        # Convert specialized report to JSON structure
        json_output = parse_specialized_report_to_json(specialized_report)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON to file
        json_file = f"specialized_report_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=4, ensure_ascii=False)
        
        return {
            "json_output": json_output,
            "json_file": json_file,
            "timestamp": timestamp
        }
        
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return {
            "error": str(e),
            "json_output": None,
            "json_file": None,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        }

# Example usage:
if __name__ == "__main__":
    # This is just for testing/demonstration purposes
    with open("form-dv-test-2.pdf", "rb") as pdf_file, open("formulaires-analyse-vt (DV).xlsx", "rb") as excel_file:
        pdf_content = pdf_file.read()
        excel_content = excel_file.read()
        
        results = analyze_real_estate_document_json(
            pdf_content, 
            excel_content
        )
        
        if "error" in results:
            print(f"Analysis failed: {results['error']}")
        else:
            print("Analysis completed successfully")
            print(f"JSON output saved to: {results['json_file']}")
            
            # Print summary of JSON content
            json_data = results["json_output"]
            print(f"\nSummary: {json_data['summary'][:100]}...")
            print(f"Recommended Actions: {len(json_data['recommended_actions'])}")
            print(f"Warnings: {len(json_data['warnings'])}")