from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = FastAPI(title="TDO Claim Copilot API")

# Allow React frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AWS Bedrock Client
# It automatically picks up the credentials from your .env file
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

class ClinicalNote(BaseModel):
    text: str

@app.post("/api/analyze-note")
async def analyze_clinical_note(note: ClinicalNote):
    try:
        # The prompt that turns Claude into a master dental biller
        system_prompt = """
        You are an expert dental billing specialist for endodontics. 
        Analyze the following clinical note and extract the exact CDT (Current Dental Terminology) codes.
        Respond ONLY in valid JSON format with the following structure:
        {
            "suggested_codes": [{"code": "D3330", "description": "Root canal - molar", "fee_estimate": 1200}],
            "total_estimated_value": 1200,
            "denial_risks": ["Mention any missing information that might cause insurance to deny this claim"],
            "status": "Ready to File" // or "Missing Info"
        }
        """

        # Construct the payload for Claude 3 on AWS Bedrock
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": f"Here is the clinical note:\n\n{note.text}"
                }
            ]
        })

        # Make the call to Claude (Replace the modelId with the exact Claude version you have access to, e.g., claude-3-haiku or sonnet)
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0', 
            contentType='application/json',
            accept='application/json',
            body=body
        )

        response_body = json.loads(response.get('body').read())
        ai_response_text = response_body['content'][0]['text']
        
        # Parse the JSON string returned by Claude into a Python dictionary
        return json.loads(ai_response_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "Backend is running!"}