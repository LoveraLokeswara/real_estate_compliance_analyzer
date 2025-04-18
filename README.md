# 📋 Real Estate Compliance Analyzer

A powerful tool for analyzing real estate documents against compliance checklists using AI to provide detailed reports and recommendations.

## 🚀 Features

- **Automated Document Analysis**: Upload PDF forms and validation checklists for instant analysis
- **AI-Powered Insights**: Leverages Claude-3.5-Sonnet for intelligent document evaluation
- **Comprehensive Reports**: Generates detailed compliance reports with actionable recommendations
- **PDF Export**: Download analysis results in professional PDF format
- **Table Support**: Properly formats and displays data tables in reports
- **Markdown Formatting**: Supports bold text and other formatting options

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/real_estate_compliance_analyzer.git
   cd real_estate_compliance_analyzer
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

## 📊 Usage

1. Start the application:
   ```bash
   streamlit run real_estate_analyzer.py
   ```

2. Use the web interface to:
   - Upload a completed PDF form
   - Upload a validation checklist Excel file
   - Click "Analyze" to process the documents
   - View the analysis results in the interface
   - Download the analysis report in PDF format

## 🧩 How It Works

1. **Document Extraction**: Extracts text from uploaded PDF documents using PyMuPDF
2. **Validation Analysis**: Compares document content against validation criteria
3. **AI Processing**: Sends the document and validation table to Claude AI for comprehensive analysis
4. **Report Generation**: Creates detailed reports with conformity scores and recommendations
5. **PDF Conversion**: Formats the analysis for downloadable PDF outputs with tables and formatting

## 📂 Project Structure

- `real_estate_analyzer.py`: Main application file with Streamlit interface and processing logic
- `standard_prompt.txt`: Template for AI analysis of documents
- `requirements.txt`: List of Python package dependencies
- `.env`: Environment variables file (not tracked in git)

## ⚙️ Dependencies

- streamlit: Web application framework
- PyMuPDF: PDF handling and text extraction
- pandas: Excel file processing
- reportlab: PDF generation
- python-dotenv: Environment variable management
- requests: API communication

## 🔍 Document Analysis Criteria

The analyzer evaluates documents based on several criteria:

- **Critical Items** (40% of total score): Mandatory documentation and critical clarifications
- **High-Risk Items** (30%): Structural elements, safety concerns, and major renovations
- **Standard Items** (20%): General information and property details
- **Administrative Items** (10%): Signatures, dates, and identification information

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details. 