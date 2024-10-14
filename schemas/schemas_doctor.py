from pydantic import BaseModel, Field
from typing import List, Optional


# Schema for doctor registration
class DoctorRegister(BaseModel):
    username: str = Field(..., title="Username of the doctor", min_length=3, max_length=30)
    password: str = Field(..., title='Password for the doctor', min_length=6)
    name: str = Field(..., title="Full name of the doctor", min_length=1)
    age: int = Field(..., title='Age of the doctor', gt=0)
    gender: str = Field(..., title="Gender of the doctor", pattern="^(Male|Female|Other)$")
    email: str = Field(..., title="Email address of the doctor")
    contact_number: str = Field(..., title="Contact number of the doctor", pattern="^\d{10}$")
    specialization: str = Field(..., title="Specialization of the doctor")
    medical_license_number: str = Field(..., title="Medical license number of the doctor")
    years_of_experience: int = Field(..., title="Years of experience of the doctor", ge=0)
    clinic_address: Optional[str] = Field(None, title="Clinic address of the doctor")
    emergency_contact_number: str = Field(..., title="Emergency contact number for the doctor", pattern="^\d{10}$")
    relationship_to_emergency_contact: str = Field(..., title="Relationship to emergency contact for the doctor")

# Schema for Doctor Login
class DoctorLogin(BaseModel):
    username: str
    password: str

    
# Schema for Doctor Response (excluding sensitive data)
class DoctorResponse(BaseModel):
    username: str = Field(..., title="Username of the doctor", min_length=3, max_length=30)
    name: str = Field(..., title="Full name of the doctor", min_length=1)
    age: int = Field(..., title='Age of the doctor', gt=0)
    gender: str = Field(..., title="Gender of the doctor", pattern="^(Male|Female|Other)$")
    email: str = Field(..., title="Email address of the doctor")
    contact_number: str = Field(..., title="Contact number of the doctor", pattern="^\d{10}$")
    specialization: str = Field(..., title="Specialization of the doctor")
    medical_license_number: str = Field(..., title="Medical license number of the doctor")
    years_of_experience: int = Field(..., title="Years of experience of the doctor", ge=0)
    clinic_address: Optional[str] = Field(None, title="Clinic address of the doctor")
    emergency_contact_number: str = Field(..., title="Emergency contact number for the doctor", pattern="^\d{10}$")
    relationship_to_emergency_contact: str = Field(..., title="Relationship to emergency contact for the doctor")


# Schema for JWT Token Response
class Token(BaseModel):
    access_token: str
    token_type: str