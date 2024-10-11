from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from fastapi import UploadFile

# Schema for patient registration
class PatientRegister(BaseModel):
    username: str = Field(..., title="Username of the patient", min_length=3, max_length=30)
    password: str = Field(..., title='Password for the patient', min_length=6)
    name: str = Field(..., title="Full name of the patient", min_length=1)
    age: int = Field(..., title='Age of the patient', gt=0)
    gender: str = Field(..., title="Gender of the patient", pattern="^(Male|Female|Other)$")
    email: str = Field(..., title="Email address of the patient")
    address: str = Field(..., title="Address of the patient")
    contact_number: str = Field(..., title="Contact number of the patient", pattern="^\d{10}$")
    date_of_birth: str = Field(..., title="Date of birth of the patient (DD-MM-YYYY)")
    height: Optional[float] = Field(None, title="Height of the patient in cm")
    weight: Optional[float] = Field(None, title="Weight of the patient in kg")
    blood_group: str = Field(..., title="Blood group of the patient", pattern="^(A|B|AB|O)[+-]$")
    emergency_contact_number: str = Field(..., title="Emergency contact number", pattern="^\d{10}$")
    relationship_to_emergency_contact: str = Field(..., title="Relationship to emergency contact")
    allergies: Optional[List[str]] = Field(None, title="Allergies of the patient (if any)")
    medical_history: Optional[List[str]] = Field(None, title="Past medical history of the patient")
    current_medications: Optional[List[str]] = Field(None, title="Current medications of the patient")
    past_surgeries_or_procedures: Optional[List[str]] = Field(None, title="Past surgeries or procedures of the patient")
    known_family_medical_history: Optional[List[str]] = Field(None, title="Known family medical history (Diabetes, Hypertension, etc.)")
    smoking_alcohol_consumption_history: Optional[str] = Field(None, title="Smoking/Alcohol consumption history of the patient")


# Schema for Patient Login
class PatientLogin(BaseModel):
    username: str
    password: str


# Schema for Patient Response (excluding sensitive data)
class PatientResponse(BaseModel):
    id: str
    username: str
    age: int


# Schema for JWT Token Response
class Token(BaseModel):
    access_token: str
    token_type: str
