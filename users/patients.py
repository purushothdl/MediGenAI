from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi.security import OAuth2PasswordBearer
from schemas import schemas_patient
from database import database
from utils import utils
from firebase_admin import credentials, initialize_app, storage
from uuid import uuid4
from confidential import bucket_id


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
        "username": patient["username"],
        "age": patient["age"]
    }


# Register route for creating new patient records
@router.post("/patient/register", response_model=schemas_patient.PatientResponse)
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
        "age": patient.age,
        "gender": patient.gender,
        "email": patient.email,
        "address": patient.address,
        "contact_number": patient.contact_number,
        "date_of_birth": patient.date_of_birth,
        "height": patient.height,
        "weight": patient.weight,
        "blood_group": patient.blood_group,
        "emergency_contact_number": patient.emergency_contact_number,
        "relationship_to_emergency_contact": patient.relationship_to_emergency_contact,
        "allergies": patient.allergies,
        "medical_history": patient.medical_history,
        "current_medications": patient.current_medications,
        "past_surgeries_or_procedures": patient.past_surgeries_or_procedures,
        "known_family_medical_history": patient.known_family_medical_history,
        "smoking_alcohol_consumption_history": patient.smoking_alcohol_consumption_history,
    }

    # Insert the new patient into the database
    result = await patients_collection.insert_one(dict(new_patient))

    # Return the inserted patient's information (excluding sensitive data)
    created_patient = await patients_collection.find_one({"_id": result.inserted_id})
    return {
        "id": str(created_patient["_id"]),
        "username": created_patient["username"],
        "name": created_patient["name"],
        "age": created_patient["age"],
        "gender": created_patient["gender"],
        "email": created_patient["email"],
        "address": created_patient["address"],
        "contact_number": created_patient["contact_number"],
        "date_of_birth": created_patient["date_of_birth"],
        "height": created_patient["height"],
        "weight": created_patient["weight"],
        "blood_group": created_patient["blood_group"],
        "emergency_contact_number": created_patient["emergency_contact_number"],
        "relationship_to_emergency_contact": created_patient["relationship_to_emergency_contact"],
        "allergies": created_patient["allergies"],
        "medical_history": created_patient["medical_history"],
        "current_medications": created_patient["current_medications"],
        "past_surgeries_or_procedures": created_patient["past_surgeries_or_procedures"],
        "known_family_medical_history": created_patient["known_family_medical_history"],
        "smoking_alcohol_consumption_history": created_patient["smoking_alcohol_consumption_history"],
    }


# Patient login endpoint
@router.post("/login", response_model=schemas_patient.Token)
async def login(patient: schemas_patient.PatientLogin, patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    
    # Retrieve the patient from the database
    db_patient = await patients_collection.find_one({"username": patient.username})

    # Check if patient exists and password is correct
    if not db_patient or not utils.verify_password(patient.password, db_patient["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Create and return JWT token
    access_token = utils.create_access_token(data={"sub": db_patient["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


# Protected endpoint that requires JWT token
@router.get("/patients/me", response_model=schemas_patient.PatientResponse)
async def read_patient_me(token: str = Depends(oauth2_scheme), patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    
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
@router.post("/patient/ticket")
async def patient_ticket(
    issue: str = Form(...),
    img: UploadFile = File(...),
    doc: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)
):
    # Decode the JWT token to get the username
    username = utils.decode_access_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    try:
        # Create a unique identifier for files
        unique_id = str(uuid4())

        # Define the path for the patient
        img_name = f"patients/{username}/images/{unique_id}_{img.filename}"
        doc_name = f"patients/{username}/documents/{unique_id}_{doc.filename}"

        bucket = storage.bucket()

        # Upload image to Firebase Cloud Storage
        if img:
            blob = bucket.blob(img_name)
            blob.upload_from_string(await img.read(), content_type=img.content_type)
            img_url = blob.public_url
        else:
            img_url = None

        # Upload document to Firebase Cloud Storage
        if doc:
            blob = bucket.blob(doc_name)
            blob.upload_from_string(await doc.read(), content_type=doc.content_type)
            doc_url = blob.public_url
        else:
            doc_url = None

        return {"issue": issue, "img_url": img_url, "doc_url": doc_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while uploading files: {str(e)}")