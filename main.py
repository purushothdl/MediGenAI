from fastapi import FastAPI
from users.patients import router as patients_router
from users.doctors import router as doctors_router
from ml_models.agents import router as analyse_router

# Adding CROS middleware
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Include the patient-related routes
app.include_router(patients_router, prefix="/api")

# Include the doctor-related routes
app.include_router(doctors_router, prefix="/api")


# For analysis
app.include_router(analyse_router, prefix="/api/doctors")
