import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import axios from 'axios';
import dotenv from 'dotenv';

// Load environment variables from .env file
dotenv.config();

// ES Module equivalent for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// The LlamaParse API key should be stored in your .env file
const LLAMAPARSE_API_KEY = process.env.LLAMAPARSE_API_KEY;

// Function to process a file with LlamaParse
async function parseDocumentWithLlamaParse(filePath: string): Promise<any> {
  try {
    // Check if file exists
    if (!fs.existsSync(filePath)) {
      throw new Error(`File not found: ${filePath}`);
    }

    // Read file as binary data
    const fileData = fs.readFileSync(filePath);
    const fileName = path.basename(filePath);
    
    // Create form data for API request
    const formData = new FormData();
    const blob = new Blob([fileData]);
    formData.append('file', blob, fileName);

    console.log(`Uploading ${fileName} to LlamaParse...`);

    // Corrected endpoint for LlamaIndex API
    const response = await axios.post('https://api.llamaindex.ai/parse', formData, {
      headers: {
        'Authorization': `Bearer ${LLAMAPARSE_API_KEY}`,
        'Content-Type': 'multipart/form-data',
      },
    });

    console.log(`Successfully parsed ${fileName}`);
    return response.data;
  } catch (error) {
    console.error('Error parsing document:', error);
    throw error;
  }
}

// Main function to demonstrate usage
async function main() {
  try {
    // Create directories if they don't exist
    const documentsDir = path.join(__dirname, 'documents');
    const outputDir = path.join(__dirname, 'output');
    
    if (!fs.existsSync(documentsDir)) {
      fs.mkdirSync(documentsDir);
      console.log('Created documents directory');
    }
    
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir);
      console.log('Created output directory');
    }
    
    // Path to your local document
    const documentPath = path.join(__dirname, 'documents', 'form-dv-test-2.pdf');
    
    // Check if document exists
    if (!fs.existsSync(documentPath)) {
      console.log(`Document not found at ${documentPath}`);
      console.log('Please make sure your document exists in the documents folder');
      return;
    }
    
    console.log(`Found document at ${documentPath}`);
    
    // Parse document
    const parsedData = await parseDocumentWithLlamaParse(documentPath);
    
    // Print the extracted data
    console.log('Parsed Content:');
    console.log(JSON.stringify(parsedData, null, 2));
    
    // Save the extracted data to a JSON file
    fs.writeFileSync(
      path.join(__dirname, 'output', 'parsed_output.json'), 
      JSON.stringify(parsedData, null, 2)
    );
    
    console.log('Parsing complete! Output saved to output/parsed_output.json');
  } catch (error) {
    console.error('Error in main function:', error);
  }
}

// Run the main function
main();