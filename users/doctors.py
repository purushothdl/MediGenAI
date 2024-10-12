from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi.security import OAuth2PasswordBearer
from schemas import schemas_doctor
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
async def get_doctor_collection() -> AsyncIOMotorCollection:
    return database.doctors_collection


# Helper function to convert MongoDB document to dictionary
def doctor_helper(doctor) -> dict:
    return {
        "id": str(doctor["_id"]),
        "username": doctor["username"],
        "age": doctor["age"],
        "specialization": doctor["specialization"]
    }


# Register route for creating new doctor records
@router.post("/doctor/register", response_model=schemas_doctor.DoctorResponse)
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
        "age": doctor.age,
        "gender": doctor.gender,
        "email": doctor.email,
        "address": doctor.address,
        "contact_number": doctor.contact_number,
        "date_of_birth": doctor.date_of_birth,
        "specialization": doctor.specialization,
        "medical_license_number": doctor.medical_license_number,
        "years_of_experience": doctor.years_of_experience,
        "clinic_address": doctor.clinic_address,
        "emergency_contact_number": doctor.emergency_contact_number,
        "relationship_to_emergency_contact": doctor.relationship_to_emergency_contact,
        "allergies": doctor.allergies,
        "medical_history": doctor.medical_history,
        "current_medications": doctor.current_medications,
        "past_surgeries_or_procedures": doctor.past_surgeries_or_procedures,
        "known_family_medical_history": doctor.known_family_medical_history,
        "smoking_alcohol_consumption_history": doctor.smoking_alcohol_consumption_history,
    }

    # Insert the new doctor into the database
    result = await doctors_collection.insert_one(dict(new_doctor))

    # Return the inserted doctor's information (excluding sensitive data)
    created_doctor = await doctors_collection.find_one({"_id": result.inserted_id})
    return {
        "id": str(created_doctor["_id"]),
        "username": created_doctor["username"],
        "name": created_doctor["name"],
        "age": created_doctor["age"],
        "gender": created_doctor["gender"],
        "email": created_doctor["email"],
        "address": created_doctor["address"],
        "contact_number": created_doctor["contact_number"],
        "date_of_birth": created_doctor["date_of_birth"],
        "specialization": created_doctor["specialization"],
        "medical_license_number": created_doctor["medical_license_number"],
        "years_of_experience": created_doctor["years_of_experience"],
        "clinic_address": created_doctor["clinic_address"],
        "emergency_contact_number": created_doctor["emergency_contact_number"],
        "relationship_to_emergency_contact": created_doctor["relationship_to_emergency_contact"],
        "allergies": created_doctor["allergies"],
        "medical_history": created_doctor["medical_history"],
        "current_medications": created_doctor["current_medications"],
        "past_surgeries_or_procedures": created_doctor["past_surgeries_or_procedures"],
        "known_family_medical_history": created_doctor["known_family_medical_history"],
        "smoking_alcohol_consumption_history": created_doctor["smoking_alcohol_consumption_history"],
    }


# Doctor login endpoint
@router.post("/login", response_model=schemas_doctor.Token)
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
@router.get("/doctors/me", response_model=schemas_doctor.DoctorResponse)
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