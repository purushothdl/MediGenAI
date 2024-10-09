from pydantic import BaseModel, Field

# Schema for patient registration
class PatientRegister(BaseModel):
    username: str = Field(..., title="Username of the patient", min_length=3, max_length=30)
    password: str = Field(..., title='Password for the patient', min_length=6)
    age: int = Field(..., title='Age of the patient', gt=0)

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
