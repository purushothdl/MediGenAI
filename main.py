from fastapi import FastAPI
from users.patients import router as patients_router
from users.doctors import router as doctors_router
from ml_models.agents import router as analyse_router

app = FastAPI()

# Include the patient-related routes
app.include_router(patients_router, prefix="/api")

# Include the doctor-related routes
app.include_router(doctors_router, prefix="/api")


# For analysis
app.include_router(analyse_router, prefix="/api/doctors")
