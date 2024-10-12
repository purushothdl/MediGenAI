from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import List
import openai
import os
from PIL import Image
import io
import easyocr
import numpy as np
import re
import pdfplumber
from confidential import openai_key



app = FastAPI()

# Set up OpenAI API key
openai.api_key = openai_key

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])  # Supports multiple languages if needed


# Define the Crew AI agents
class Agent1:
    def __init__(self):
        pass

    async def run(self, files):
        text_data = []
        vision_data = []
        
        # Extract data from images and documents using EasyOCR and OpenAI models
        for file in files:
            content = await file.read()
            if file.content_type.startswith("image/"):
                # Use EasyOCR to extract text from the image
                image = Image.open(io.BytesIO(content))
                image_np = np.array(image)
                extracted_text = reader.readtext(image_np, detail=0)
                extracted_text_str = " ".join(extracted_text)

                # Use OpenAI to analyze the extracted text
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": f"Analyze the following text extracted from an image:\n{extracted_text_str}"}],
                    max_tokens=1000
                )
                vision_data.append(response['choices'][0]['message']['content'])
            elif file.content_type == "application/pdf":
                # Use pdfplumber to extract text from PDF
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    pdf_text = ""
                    for page in pdf.pages:
                        pdf_text += page.extract_text() + "\n"
                
                # Using OpenAI to analyze text content from PDF
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": f"Extract key medical entities from the following text:\n{pdf_text}"}],
                    max_tokens=1000
                )
                text_data.append(response['choices'][0]['message']['content'])

        return {"text_data": text_data, "vision_data": vision_data}

class Agent2:
    async def run(self, context):
        # Use OpenAI to generate recommended specialists based on the context
        all_text = " ".join(context.get("text_data", []) + context.get("vision_data", []))

        # Use OpenAI to generate recommendations
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Based on the following medical text, recommend the appropriate medical specialists and indicate if any are mandatory:\n{all_text}"}],
            max_tokens=500
        )
        recommendations_text = response['choices'][0]['message']['content'].split('\n')

        # Clean up recommendations list and categorize mandatory specialists
        recommendations = []
        mandatory = []
        for rec in recommendations_text:
            if rec.strip():
                if "mandatory" in rec.lower():
                    mandatory.append(rec.replace("(mandatory)", "").strip())
                else:
                    recommendations.append(rec.strip())

        return {"recommendations": recommendations, "mandatory": mandatory}

class Agent3:
    async def run(self, context, recommendations):
        # Compile a final report based on the recommendations
        final_report = {
            "context_summary": context,
            "recommended_specialists": {
                "recommendations": recommendations.get("recommendations", []),
                "mandatory": recommendations.get("mandatory", [])
            },
            "overall_evaluation": "The patient shows potential signs that may require attention from the listed specialists."
        }
        return final_report

# Initialize agents
agent_1 = Agent1()
agent_2 = Agent2()
agent_3 = Agent3()

# Define the /analyze route
@app.post("/analyze")
async def analyze(ticket_id: str, files: List[UploadFile] = File(...)):
    try:
        # Step 1: Initial Analysis by Agent 1
        context = await agent_1.run(files)

        # Step 2: Recommendation by Agent 2
        recommendations = await agent_2.run(context)

        # Step 3: Final Evaluation by Agent 3
        final_report = await agent_3.run(context, recommendations)

        # Return the final compiled analysis
        return {
            "ticket_id": ticket_id,
            "analysis": final_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))