from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi.security import OAuth2PasswordBearer
from schemas import schemas_doctor
from database import database
from utils import utils
from firebase_admin import credentials, initialize_app, storage, get_app
from uuid import uuid4
from confidential import bucket_id
import os
import sys
from bson import ObjectId
import json



# Set the path to the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


router = APIRouter()

# Define the OAuth2PasswordBearer instance to retrieve the JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Initialize Firebase Admin SDK
try:
    app = get_app()
except ValueError:
    cred = credentials.Certificate("serviceAccountKey.json")
    initialize_app(cred, {'storageBucket': bucket_id})


# Dependency to get the MongoDB collection
async def get_doctor_collection() -> AsyncIOMotorCollection:
    return database.doctors_collection

# Helper function to convert MongoDB document to dictionary
def doctor_helper(doctor) -> dict:
    return {
        "age": int(doctor.get("age", 0)) if doctor.get("age") is not None else 0,
        "id": str(doctor["_id"]),
        "username": doctor["username"],
        "specialization": doctor["specialization"],
        "medical_license_number": doctor["medical_license_number"],
        "years_of_experience": doctor["years_of_experience"],
        "clinic_address": doctor.get("clinic_address"),
        "name": doctor.get("name"),
        "gender": doctor.get("gender"),
        "email": doctor.get("email"),
        "contact_number": doctor.get("contact_number"),
        "emergency_contact_number": doctor.get("emergency_contact_number"),
        "relationship_to_emergency_contact": doctor.get("relationship_to_emergency_contact")
    }

# Register route for creating new doctor records
@router.post("/doctor/register", response_model=schemas_doctor.DoctorResponse, tags=['Doctors'])
async def register_doctor(doctor: schemas_doctor.DoctorRegister, 
                          doctors_collection: AsyncIOMotorCollection = Depends(get_doctor_collection)):
    # Check if username already exists
    existing_doctor = await doctors_collection.find_one({"username": doctor.username})
    if existing_doctor:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Hash the password
    hashed_password = utils.hash_password(doctor.password)

    # Create a new doctor record
    new_doctor = {
        "username": doctor.username,
        "hashed_password": hashed_password,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "medical_license_number": doctor.medical_license_number,
        "years_of_experience": doctor.years_of_experience,
        "clinic_address": doctor.clinic_address,
        "contact_number": doctor.contact_number,
        "emergency_contact_number": doctor.emergency_contact_number,
        "relationship_to_emergency_contact": doctor.relationship_to_emergency_contact,
        "age": doctor.age,
        "gender": doctor.gender,
        "email": doctor.email
    }

    # Insert the new doctor into the database
    result = await doctors_collection.insert_one(dict(new_doctor))

    # Return a success message
    return {"message": "Registration successful"}



# Doctor login endpoint
@router.post("/doctors/login", response_model=schemas_doctor.Token, tags=['Doctors'])
async def login(doctor: schemas_doctor.DoctorLogin, doctors_collection: AsyncIOMotorCollection = Depends(get_doctor_collection)):
    # Retrieve the doctor from the database
    db_doctor = await doctors_collection.find_one({"username": doctor.username})

    # Check if doctor exists and password is correct
    if not db_doctor or not utils.verify_password(doctor.password, db_doctor["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Create and return JWT token
    access_token = utils.create_access_token(data={"sub": db_doctor["username"]})
    return {"access_token": access_token, "token_type": "bearer"}



# Protected endpoint that requires JWT token
@router.get("/doctors/me", response_model=schemas_doctor.DoctorResponse, tags=['Doctors'])
async def read_doctor_me(token: str = Depends(oauth2_scheme), doctors_collection: AsyncIOMotorCollection = Depends(get_doctor_collection)):
    # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Retrieve the doctor from the database using the username
    db_doctor = await doctors_collection.find_one({"username": username})
    if db_doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Return the doctor information (excluding sensitive data)
    return doctor_helper(db_doctor)


# Dependency to get the patients MongoDB collection
async def get_patient_collection() -> AsyncIOMotorCollection:
    return database.patients_collection


# Route for doctors to view all patients
@router.get("/doctors/view_patients", tags=['Doctors'])
async def view_patients(token: str = Depends(oauth2_scheme), patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Retrieve all patients from the database
    patients_cursor = patients_collection.find()
    patients = await patients_cursor.to_list(length=100)

    # Convert each patient document to dictionary
    patients_list = [
        {
            "id": str(patient["_id"]),
            "username": patient["username"],
            "name": patient.get("name"),
            "age": patient.get("age"),
            "gender": patient.get("gender"),
            "email": patient.get("email"),
            "address": patient.get("address"),
            "contact_number": patient.get("contact_number"),
            "date_of_birth": patient.get("date_of_birth"),
            "height": patient.get("height"),
            "weight": patient.get("weight"),
            "blood_group": patient.get("blood_group"),
            "emergency_contact_number": patient.get("emergency_contact_number"),
            "relationship_to_emergency_contact": patient.get("relationship_to_emergency_contact"),
            "allergies": patient.get("allergies"),
            "medical_history": patient.get("medical_history"),
            "current_medications": patient.get("current_medications"),
            "past_surgeries_or_procedures": patient.get("past_surgeries_or_procedures"),
            "known_family_medical_history": patient.get("known_family_medical_history"),
            "smoking_alcohol_consumption_history": patient.get("smoking_alcohol_consumption_history")
        }
        for patient in patients
    ]

    return {"patients": patients_list}



# Route for doctors to view all tickets of a specific patient
@router.get("/doctors/view_patient_tickets/{patient_id}", tags=['Doctors'])
async def view_patient_tickets(patient_id: str, token: str = Depends(oauth2_scheme), patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Retrieve the specific patient from the database
    from bson import ObjectId
    patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Extract tickets from the patient record
    tickets = patient.get("tickets", [])

    # Convert each ticket to dictionary
    tickets_list = [
        {
            "ticket_id": ticket.get("ticket_id"),
            "issue": ticket.get("issue"),
            "status": ticket.get("status")
        }
        for ticket in tickets
    ]

    return {"tickets": tickets_list}



# Route for doctors to view the past patient analysis files (past files stored in firebase)
@router.get("/doctors/view_patient_files/{patient_id}", tags=['Doctors'])
async def view_patient_reports_by_id(
    patient_id: str, 
    token: str = Depends(oauth2_scheme),
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):

    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


    try:
        # Retrieve the specific patient from the database
        patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Construct the path for retrieving all past reports from Firebase
        bucket = storage.bucket()
        report_folder_prefix = f"preliminary_analysis/{patient['username']}/"

        # List all blobs under the patient's username folder
        blobs = bucket.list_blobs(prefix=report_folder_prefix)
        report_files = []
        for blob in blobs:
            # Extracting the issue and ticket_id from the folder name
            folder_name = blob.name.split('/')[-2]
            if folder_name not in report_files:
                report_files.append(folder_name)

        # Return the list of all patient reports
        return {
            "patient_id": patient_id,
            "reports": report_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Define the /doctors/send_final_report route
@router.post("/doctors/send_final_report", tags=['Doctors'])
async def send_final_report(
    ticket_id: str = Form(...),
    token: str = Depends(oauth2_scheme),
    patient_id: str = Form(...),
    report_content: str = Form(...),
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):

    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

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

        # Construct the path for storing the final report in Firebase
        bucket = storage.bucket()
        final_report_folder = f"final_reports/{patient['username']}/{issue+'_'+str(ticket_id)}"
        final_report_path = f"{final_report_folder}/final_report.doc"
        blob = bucket.blob(final_report_path)
        blob.upload_from_string(report_content, content_type="application/msword")

        # Update the ticket status to "Final Report Submitted" in the patient database
        await patients_collection.update_one(
            {"_id": ObjectId(patient_id), "tickets.ticket_id": ticket_id},
            {"$set": {"tickets.$.status": "Final Report Submitted"}}
        )

        return {
            "ticket_id": ticket_id,
            "message": "Final report successfully submitted."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Route where the doctors can view in detail about the patients past analysis report 
@router.get("/doctors/view_past_analysis/{patient_id}/{issue_ticketid}", tags=['Doctors'])
async def view_patient_report_json(
    patient_id: str,
    issue_ticketid: str,
    token: str = Depends(oauth2_scheme),
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):

    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    try:
        # Retrieve the specific patient from the database
        patient = await patients_collection.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Construct the path for the specific report in Firebase
        bucket = storage.bucket()
        report_path = f"preliminary_analysis/{patient['username']}/{issue_ticketid}/report.json"

        # Check if the report exists
        blob = bucket.blob(report_path)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        # Download the JSON content
        report_content = blob.download_as_string()
        report_json = json.loads(report_content)

        # Return the JSON content directly
        return {
            "patient_id": patient_id,
            "issue_ticketid": issue_ticketid,
            "report": report_json
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





# Define the /doctors/feedback route
@router.post("/doctors/feedback", tags=['Feedback'])
async def submit_feedback(
    feedback: str = Form(...),
    role: str = Form(...),
    token: str = Depends(oauth2_scheme)
):
    try:
        # Decode the JWT token to validate it
        username = utils.decode_access_token(token)
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")

        # Construct the path for the feedback in Firebase
        bucket = storage.bucket()
        feedback_path = f"feedback/doctor/{username}/feedback.json"
        feedback_data = {
            "username": username,
            "role": role,
            "feedback": feedback
        }

        # Store the feedback data as a JSON file in Firebase
        blob = bucket.blob(feedback_path)
        blob.upload_from_string(json.dumps(feedback_data), content_type="application/json")

        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))