from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Request
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi.security import OAuth2PasswordBearer
from schemas import schemas_patient
from database import database
from utils import utils
from firebase_admin import credentials, initialize_app, storage, get_app
from uuid import uuid4
from confidential import bucket_id
import json
from typing import List,  Optional
from bson import ObjectId
from datetime import datetime
import mimetypes
from transformers import pipeline
import tf_keras
from sklearn.feature_extraction.text import TfidfVectorizer
import httpx

router = APIRouter()


# Define the OAuth2PasswordBearer instance to retrieve the JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
initialize_app(cred, {'storageBucket': bucket_id})


# Dependency to get the MongoDB collection
async def get_patient_collection() -> AsyncIOMotorCollection:
    return database.patients_collection


# Helper function to convert MongoDB document to dictionary
def patient_helper(patient) -> dict:
    return {
        "id": str(patient["_id"]),
        "username": str(patient["username"]),
        "name": str(patient.get("name", "")),
        "age": int(patient.get("age", 0)),
        "gender": str(patient.get("gender", "")),
        "email": str(patient.get("email", "")),
        "address": str(patient.get("address", "")),
        "contact_number": str(patient.get("contact_number", "")),
        "date_of_birth": str(patient.get("date_of_birth", "")),
        "height": float(patient.get("height", 0.0)),
        "weight": float(patient.get("weight", 0.0)),
        "blood_group": str(patient.get("blood_group", "")),
        "emergency_contact_number": str(patient.get("emergency_contact_number", "")),
        "relationship_to_emergency_contact": str(patient.get("relationship_to_emergency_contact", "")),
        "allergies": list(patient.get("allergies", [])),
        "medical_history": list(patient.get("medical_history", [])),
        "current_medications": list(patient.get("current_medications", [])),
        "past_surgeries_or_procedures": list(patient.get("past_surgeries_or_procedures", [])),
        "known_family_medical_history": list(patient.get("known_family_medical_history", [])),
        "smoking_alcohol_consumption_history": str(patient.get("smoking_alcohol_consumption_history", ""))
    }


# Register route for creating new patient records
@router.post("/patients/register", tags=["Patients"])
async def register_patient(patient: schemas_patient.PatientRegister, 
                           patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    
    # Check if username already exists
    existing_patient = await patients_collection.find_one({"username": patient.username})
    if existing_patient:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Hash the password
    hashed_password = utils.hash_password(patient.password)

    # Create a new patient record
    new_patient = {
        "username": patient.username,
        "hashed_password": hashed_password,
        "name": patient.name,
    }

    # Insert the new patient into the database
    result = await patients_collection.insert_one(dict(new_patient))

    # Return a success message
    return {"message": "Registration successful"}



# Patient login endpoint
@router.post("/patients/login", response_model=schemas_patient.Token, tags=["Patients"])
async def login(patient: schemas_patient.PatientLogin, patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    
    # Retrieve the patient from the database
    db_patient = await patients_collection.find_one({"username": patient.username})

    # Check if patient exists and password is correct
    if not db_patient or not utils.verify_password(patient.password, db_patient["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Create and return JWT token
    access_token = utils.create_access_token(data={"sub": db_patient["username"]})
    return {"access_token": access_token, "token_type": "bearer"}



# Update route for adding patient details
@router.post("/patients/update_details/{patient_id}", tags=["Patients"])
async def update_patient_details(
    patient_id: str,
    patient: schemas_patient.PatientUpdate,
    token: str = Depends(oauth2_scheme),
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)
):
    # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Find the patient by patient ID
    if not ObjectId.is_valid(patient_id):
        raise HTTPException(status_code=400, detail="Invalid patient ID")

    existing_patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
    if not existing_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update patient details
    updated_fields = {key: value for key, value in patient.dict().items() if value is not None}
    if not updated_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    await patients_collection.update_one({"_id": ObjectId(patient_id)}, {"$set": updated_fields})

    # Return a success message
    return {"message": "Patient details updated successfully"}




# Protected endpoint that requires JWT token
@router.get("/patients/me", response_model=schemas_patient.PatientResponse, tags=["Patients"])
async def read_patient_me(token: str = Depends(oauth2_scheme), 
                          patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    
    # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Retrieve the patient from the database using the username
    db_patient = await patients_collection.find_one({"username": username})
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Return the patient information (excluding sensitive data)
    return patient_helper(db_patient)



# Patient ticket endpoint to upload images and documents
@router.post("/patients/ticket", tags=["Patients"])
async def patient_ticket(
    issue: str = Form(...),
    imgs: List[UploadFile] = File(None),
    docs: List[UploadFile] = File(None),
    token: str = Depends(oauth2_scheme),
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)
):
 # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    try:
        # Generate a unique ticket ID
        ticket_id = str(uuid4())

        # Initialize bucket
        bucket = storage.bucket()

        # Upload images to Firebase Cloud Storage
        img_urls = []
        if imgs:
            for img in imgs:
                if img:
                    unique_id = str(uuid4())
                    img_name = f"patients/{username}/{issue+'_'+str(ticket_id)}/images/{unique_id}_{img.filename}"
                    blob = bucket.blob(img_name)
                    blob.upload_from_string(await img.read(), content_type=img.content_type)
                    # Validate the uploaded file
                    file_type = mimetypes.guess_type(img.filename)[0]
                    if not file_type or not file_type.startswith("image/"):
                        # Delete the invalid file
                        blob.delete()
                    else:
                        img_urls.append(blob.public_url)

        # Upload documents to Firebase Cloud Storage
        doc_urls = []
        if docs:
            for doc in docs:
                if doc:
                    unique_id = str(uuid4())
                    doc_name = f"patients/{username}/{issue+'_'+str(ticket_id)}/documents/{unique_id}_{doc.filename}"
                    blob = bucket.blob(doc_name)
                    blob.upload_from_string(await doc.read(), content_type=doc.content_type)
                    # Validate the uploaded file
                    file_type = mimetypes.guess_type(doc.filename)[0]
                    if not file_type or file_type not in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                        # Delete the invalid file
                        blob.delete()
                    else:
                        doc_urls.append(blob.public_url)

        # Insert ticket information into the database only if images or documents are uploaded
        if img_urls or doc_urls:
            ticket_data = {
                "username": username,
                "issue": issue,
                "img_urls": img_urls,
                "status": "In Progress",
                "doc_urls": doc_urls,
                "ticket_id": ticket_id,
                "created_at": datetime.utcnow().strftime('%d-%m-%Y')
            }
            await patients_collection.update_one(
                {"username": username},
                {"$push": {"tickets": ticket_data}}
            )
        return {"ticket_id": ticket_id, "issue": issue, "created_at": ticket_data["created_at"], "status": "Documents uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while uploading files: {str(e)}")



# Route to view all tickets of the patient
@router.get("/patients/view_all_tickets", tags=["Patients"])
async def view_all_tickets(token: str = Depends(oauth2_scheme), patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Retrieve the patient from the database using the username
    db_patient = await patients_collection.find_one({"username": username})
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Retrieve all tickets for the patient, excluding image and document URLs
    tickets = [{

        "ticket_id": ticket.get("ticket_id"),
        "username": ticket.get("username"),
        "issue": ticket.get("issue"),
        "created_at": ticket.get("created_at"),
        "img_url": ticket.get("img_urls"),
        "doc_url": ticket.get("doc_urls"),
        "status": ticket.get("status"),
           
    } for ticket in db_patient.get("tickets", [])]

    return {"username": username, "tickets": tickets}



# # Route to view the status of a specific ticket
# @router.get("/patients/ticket_status/{ticket_id}", tags=["Patients"])
# async def view_ticket_status(ticket_id: str, token: str = Depends(oauth2_scheme), patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
#     # Decode the JWT token to get the username
#     username = utils.decode_access_token(token)
#     if username is None:
#         raise HTTPException(status_code=401, detail="Could not validate credentials")

#     # Retrieve the patient from the database using the username
#     db_patient = await patients_collection.find_one({"username": username})
#     if db_patient is None:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Find the specific ticket
#     ticket = next((t for t in db_patient.get("tickets", []) if t.get("ticket_id") == ticket_id), None)
#     if ticket is None:
#         raise HTTPException(status_code=404, detail="Ticket not found")

#     return {"ticket_id": ticket_id, "status": ticket.get("status")}



# Route to view the analysis report of a specific ticket
@router.get("/patients/view_doctor_report", tags=["Patients"])
async def view_doctor_report(
    patient_id: str,
    issue: str,
    ticket_id: str,
    token: str = Depends(oauth2_scheme),
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    try:
        # Retrieve the specific patient from the database
        patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        ticket = patient.get("tickets", [])

        # Construct the path for the specific doctor's final report in Firebase
        bucket = storage.bucket()
        report_path = f"final_reports/{patient['username']}/{issue}_{ticket_id}/final_report.doc"

        # Check if the report exists
        blob = bucket.blob(report_path)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Doctor's final report not found")

        # Download the report content
        report_content = blob.download_as_string()

        # Return the report content directly
        return {
            "patient_id": patient_id,
            "ticket_id": ticket_id,
            "created_at": next((ticket.get("created_at") for ticket in patient.get("tickets", []) if ticket.get("ticket_id") == ticket_id), ""),
            "issue": issue,
            "report_content": report_content.decode("utf-8")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Define the /patients/feedback route
@router.post("/patients/feedback", tags=['Feedback'])
async def submit_feedback(
    title: str = Form(...),
    feedback: str = Form(...),
    token: str = Depends(oauth2_scheme)
):
    try:
        # Decode the JWT token to validate it
        username = utils.decode_access_token(token)
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")

        # Construct the path for the feedback in Firebase
        bucket = storage.bucket()
        feedback_path = f"feedback/patient/{username}/feedback.json"
        feedback_data = {
            "username": username,
            "title": title,
            "feedback": feedback
        }

        # Store the feedback data as a JSON file in Firebase
        blob = bucket.blob(feedback_path)
        blob.upload_from_string(json.dumps(feedback_data), content_type="application/json")

        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    





        
# # Route to create a general chatbot for patients using Google Gemini API
# @router.post("/patients/chatbox", tags=["Patients"])
# async def patients_chatbox(
#     request: Request,
#     token: str = Depends(oauth2_scheme),
#     patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)
# ):
#     try:
#         # Get the patient message from request body
#         body = await request.json()
#         message = body.get("message")
#         if not message:
#             raise HTTPException(status_code=400, detail="Message is required")

#         # Use Google Gemini API to generate a response based on the user question
#         async with httpx.AsyncClient() as client:
#             gemini_api_key = "AIzaSyAurS4kzapMMz3_vIaM-aoNaccxx7x9_hg"
#             response = await client.post(
#                 "https://gemini.googleapis.com/v1beta/chat:complete",
#                 headers={
#                     "Authorization": f"Bearer {gemini_api_key}",
#                     "Content-Type": "application/json"
#                 },
#                 json={
#                     "prompt": message,
#                     "model": "chat-bison",  # Example model name, adjust as needed
#                     "temperature": 0.7,
#                     "maxTokens": 150
#                 }
#             )
#             if response.status_code == 200:
#                 response_data = response.json()
#                 candidates = response_data.get("candidates", [])
#                 if candidates:
#                     gemini_response = candidates[0].get("content", "I'm here to help you. Could you please provide more details?")
#                 else:
#                     gemini_response = "I'm here to help you. Could you please provide more details?"
#             else:
#                 raise HTTPException(status_code=response.status_code, detail=f"Error from Gemini API: {response.text}")
#         # Return the response to the patient
#         return {"response": gemini_response}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))