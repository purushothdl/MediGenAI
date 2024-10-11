from fastapi import FastAPI
from patients import router as patients_router

app = FastAPI()

# Include the patient-related routes
app.include_router(patients_router, prefix="/api")

# Placeholder for including doctor-related routes in the future
# from doctors import router as doctors_router
# app.include_router(doctors_router, prefix="/api")
