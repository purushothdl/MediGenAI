from fastapi import HTTPException, APIRouter, FastAPI, Form, Depends
from motor.motor_asyncio import AsyncIOMotorCollection
from firebase_admin import credentials, initialize_app, storage, get_app
import numpy as np
import io
from PIL import Image
import easyocr
import fitz  # PyMuPDF
from groq import Groq
from bson import ObjectId
import json
from database import database
from confidential import bucket_id, groq_key

# Set up Firebase Admin SDK
try:
    app = get_app()
except ValueError:
    cred = credentials.Certificate("serviceAccountKey.json")
    initialize_app(cred, {'storageBucket': bucket_id})

# Set up Groq API key
client = Groq(
    api_key=groq_key,
)

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

router = APIRouter()

# Dependency to get the patients MongoDB collection
async def get_patient_collection() -> AsyncIOMotorCollection:
    return database.patients_collection

# Extract text from image using EasyOCR
def extract_text_from_image(image: Image.Image):
    try:
        # Convert the image to a NumPy array
        image_np = np.array(image)
        
        # Extract text from the image using EasyOCR
        results = reader.readtext(image_np, detail=0)  # detail=0 returns only the text
        
        # Combine extracted text into a single string
        extracted_text = "\n".join(results)
        
        return extracted_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {e}")

# Extract text from PDF using PyMuPDF (Fitz)
def extract_text_from_pdf(pdf_content: bytes):
    try:
        # Open the PDF from bytes
        document = fitz.open(stream=pdf_content, filetype="pdf")
        pdf_text = []
        
        # Iterate through pages and extract text
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text = page.get_text()
            pdf_text.append(text)
        
        # Combine all page texts into a single string
        combined_text = "\n".join(pdf_text)
        
        return combined_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {e}")

# Analyze text using Groq
def analyze_text_with_groq(extracted_text: str):
    try:
        # Use Groq to analyze the extracted text
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": f"Analyze the following text extracted from a document and give the inference in paragraph (preferably 10 lines):\n{extracted_text}"}]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text with Groq: {e}")

# Main function to process files from Firebase Storage
async def process_file_from_firebase(file_path: str):
    try:
        # Get the bucket and download the file
        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found in Firebase storage.")
        
        content = blob.download_as_bytes()
        
        # Check file type and extract text accordingly
        if file_path.endswith(".pdf"):
            extracted_text = extract_text_from_pdf(content)
        else:
            image = Image.open(io.BytesIO(content))
            extracted_text = extract_text_from_image(image)
        
        # Analyze the extracted text using Groq
        analysis_result = analyze_text_with_groq(extracted_text)
        
        return {
            "extracted_text": extracted_text,
            "analysis": analysis_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Define the /analyze route
@router.post("/analyze", tags=['Analysis'])
async def analyze(
    ticket_id: str = Form(...), 
    patient_id: str = Form(...), 
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    try:
        # Retrieve the specific patient from the database
        patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Retrieve the issue from the patient's tickets
        ticket = next((ticket for ticket in patient.get("tickets", []) if ticket.get("ticket_id") == ticket_id), None)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        issue = ticket.get("issue")
        if not issue:
            raise HTTPException(status_code=404, detail="Issue not found in ticket")

        # Construct the path for patient files in Firebase
        bucket = storage.bucket()
        ticket_folder = f"patients/{patient['username']}/{issue}_{ticket_id}"
        images_folder = f"{ticket_folder}/images/"
        documents_folder = f"{ticket_folder}/documents/"

        # Retrieve all files from Firebase Storage
        blobs = bucket.list_blobs(prefix=ticket_folder)
        files = [blob for blob in blobs if blob.name.startswith(images_folder) or blob.name.startswith(documents_folder)]

        # vision_data = []
        # text_data = []
        individual_reports = []

        for file in files:
            content = file.download_as_bytes()
            report = {
                "file_name": file.name,
                "type": "image" if file.content_type.startswith("image/") else "text",
                "extracted_text": "",
                "analysis": ""
            }

            if file.content_type.startswith("image/"):
                # Extract text from the image
                image = Image.open(io.BytesIO(content))
                extracted_text = extract_text_from_image(image)
                report["extracted_text"] = extracted_text

                # Use Groq to analyze the extracted text
                analysis_result = analyze_text_with_groq(extracted_text)
                report["analysis"] = analysis_result
                # vision_data.append(analysis_result)

            elif file.content_type == "application/pdf":
                # Extract text from the PDF
                extracted_text = extract_text_from_pdf(content)
                # report["extracted_text"] = extracted_text

                # Use Groq to analyze the extracted text
                analysis_result = analyze_text_with_groq(extracted_text)
                report["analysis"] = analysis_result
                # text_data.append(analysis_result)

                    
            # Generate individual recommendations for each file
            individual_response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", 
                           "content": f"""
                                Based on the following text, provide a list of medical specialists needed, 
                                along with reasons for why each specialist is required:{extracted_text}"""}])
            
            individual_recommendations_text = individual_response.choices[0].message.content.splitlines()

            individual_recommendations = []
                        
            for rec in individual_recommendations_text:
                if rec.strip():
                    individual_recommendations.append(rec.strip())
 
            
            # Add recommendations and mandatory to individual report
            report["specialists"] = individual_recommendations

            individual_reports.append(report)


        # Compile a final report
        final_report = {
            "individual_reports": individual_reports,
            "overall_evaluation": f"""The analysis indicates potential health concerns that should be addressed by the listed specialists. 
            Each specialist is recommended based on their expertise in managing the identified issues."""
        }

        # Update the ticket status to "Analysis Completed" in the patient database
        await patients_collection.update_one(
            {"_id": ObjectId(patient_id), "tickets.ticket_id": ticket_id},
            {"$set": {"tickets.$.status": "Analysis Completed"}}
        )

        # Store the preliminary analysis report in Firebase
        prelim_report_folder = f"preliminary_analysis/{patient['username']}/{issue+'_'+str(ticket_id)}"
        prelim_report_path = f"{prelim_report_folder}/report.json"
        blob = bucket.blob(prelim_report_path)
        blob.upload_from_string(json.dumps(final_report), content_type="application/json")

        # Return the final compiled analysis
        return {
            "ticket_id": ticket_id,
            "analysis": final_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))