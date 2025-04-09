# Real Estate Compliance Analyzer

## Overview
The Real Estate Compliance Analyzer is a Streamlit application designed to analyze real estate documents, specifically "Déclarations du vendeur" (DV) forms, against a detailed validation checklist. This application utilizes AI to provide insights and recommendations based on the analysis of the uploaded documents.

## Project Structure
This project consists of the following key files:

### 1. `requirements.txt`
This file lists all the Python packages required to run the application. The dependencies include:

- **streamlit**: A framework for building web applications.
- **openai**: For AI model interactions.
- **python-dotenv**: To load environment variables from a `.env` file.
- **pandas**: For data manipulation and analysis.
- **PyMuPDF**: For handling PDF files.
- **openpyxl**: For reading Excel files.
- **numpy**: For numerical operations.
- **faiss-cpu**: For efficient similarity search and clustering.
- **sentence-transformers**: For natural language processing tasks.
- **PyPDF2**: For PDF file manipulation.
- **pdf2image**: For converting PDF pages to images.
- **pytesseract**: For optical character recognition (OCR).
- **requests**: For making HTTP requests.
- **reportlab**: For generating PDF documents.

### 2. `standard_prompt.txt`
This file contains the standard prompt used by the AI model to analyze the DV form. It outlines the evaluation criteria, including conformity checks for each section (DV1 to DV16) and provides a structured format for the AI's output. The AI will assess the completeness and correctness of the form and provide a conformity score.

### 3. `specialized_prompt.txt`
This file contains a more detailed prompt for the AI model, focusing on specialized analysis. It instructs the AI to identify specific issues, recommend actions, and provide HR tips, warnings, and required training based on the analysis of the DV form. The output is formatted to ensure clarity and comprehensiveness.

## Usage
1. **Install Dependencies**: Ensure you have Python installed, then run the following command to install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment Variables**: Create a `.env` file in the project root and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

3. **Run the Application**: Start the Streamlit application by executing:
   ```bash
   streamlit run real_estate_analyzer.py
   ```

4. **Upload Documents**: Use the web interface to upload the completed PDF form and the checklist Excel file for analysis.

5. **Analyze**: Click the "Analyze" button to process the documents. The application will provide analysis results and allow you to download the reports in PDF format.

## Conclusion
This README provides a brief overview of the Real Estate Compliance Analyzer project, its structure, and how to use it effectively. For further assistance, please refer to the documentation of the respective libraries or the Streamlit documentation. 