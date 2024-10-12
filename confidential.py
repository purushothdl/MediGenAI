from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Access the environment variables
bucket_id = os.getenv("BUCKET_ID")
mongo_uri = os.getenv("MONGO_URI")
openai_key = os.getenv("OPENAI_KEY")


