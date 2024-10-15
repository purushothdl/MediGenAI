from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from fastapi import UploadFile

# Schema for patient registration
class PatientRegister(BaseModel):
    username: str = Field(..., title="Username of the patient", min_length=3, max_length=30)
    password: str = Field(..., title='Password for the patient', min_length=6)
    name: str = Field(..., title="Full name of the patient", min_length=1)


# Schema for Patient Login
class PatientLogin(BaseModel):
    username: str
    password: str

class PatientUpdate(BaseModel):
    username: str = Field(..., title="Username of the patient", min_length=3, max_length=30)
    name: str = Field(..., title="Full name of the patient", min_length=1)
    age: Optional[int] = 0
    gender: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    contact_number: Optional[str] = ""
    date_of_birth: Optional[str] = ""
    height: Optional[float] = 0.0
    weight: Optional[float] = 0.0
    blood_group: Optional[str] = ""
    emergency_contact_number: Optional[str] = ""
    relationship_to_emergency_contact: Optional[str] = ""
    allergies: Optional[List[str]] = []
    medical_history: Optional[List[str]] = []
    current_medications: Optional[List[str]] = []
    past_surgeries_or_procedures: Optional[List[str]] = []
    known_family_medical_history: Optional[List[str]] = []
    smoking_alcohol_consumption_history: Optional[str] = ""


# Schema for Patient Response (excluding sensitive data)
class PatientResponse(BaseModel):
    id: str
    username: str
    name: str
    age: int
    gender: str
    email: str
    address: str
    contact_number: str
    date_of_birth: str
    height: float
    weight: float
    blood_group: str
    emergency_contact_number: str
    relationship_to_emergency_contact: str
    allergies: List[str]
    medical_history: List[str]
    current_medications: List[str]
    past_surgeries_or_procedures: List[str]
    known_family_medical_history: List[str]
    smoking_alcohol_consumption_history: str


# Schema for JWT Token Response
class Token(BaseModel):
    access_token: str
    token_type: str
