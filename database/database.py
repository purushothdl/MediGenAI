from motor.motor_asyncio import AsyncIOMotorClient
import confidential

# MONGODB_URL = "mongodb+srv://jeankirstein6104:UaSXsPMMz99Acj9v@projects.g4su2.mongodb.net/?retryWrites=true&w=majority&appName=projects"

MONGODB_URL = confidential.mongo_uri

# Create a MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)

# Define the MongoDB database
database = client.medical_data

# Define the collection for patients
patients_collection = database.patients