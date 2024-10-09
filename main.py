from fastapi import FastAPI, Depends, HTTPException, status
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from schemas import schemas
from database import database
from utils import utils

app = FastAPI()

# Define the OAuth2PasswordBearer instance to retrieve the JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


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
@app.post("/patient/register", response_model=schemas.PatientResponse)
async def register_patient(patient: schemas.PatientRegister, patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
    
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
        "age": patient.age,
    }

    # Insert the new patient into the database
    result = await patients_collection.insert_one(new_patient)

    # Return the inserted patient's information (excluding sensitive data)
    created_patient = await patients_collection.find_one({"_id": result.inserted_id})
    return {"id": str(created_patient["_id"]), "username": created_patient["username"], "age": created_patient["age"]}
   

# Patient login endpoint
@app.post("/login", response_model=schemas.Token)
async def login(patient: schemas.PatientLogin, patients_collection: AsyncIOMotorCollection = Depends(get_patient_collection)):
        
    # Retrieve the patient from the database
    db_patient = await patients_collection.find_one({"username": patient.username})
    
    # Check if patient exists and password is correct
    if not db_patient or not utils.verify_password(patient.password, db_patient["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Create and return JWT token
    access_token = utils.create_access_token(data={"sub": db_patient["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


# Protected endpoint that requires JWT token
@app.get("/patients/me", response_model=schemas.PatientResponse)
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