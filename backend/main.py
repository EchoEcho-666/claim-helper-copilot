import boto3
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = FastAPI(title="Claim Helper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Boto3 automatically uses the keys in your .env file
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)


# --- CDT Reference Data ---

def load_cdt_reference():
    """Load CDT codes from mock JSON at startup."""
    cdt_path = Path(__file__).parent / "data" / "cdt_mock.json"
    with open(cdt_path) as f:
        data = json.load(f)
    # Build a lookup dict keyed by code
    return {entry["code"]: entry for entry in data["codes"]}

CDT_CODES = load_cdt_reference()


def match_cdt_codes(ai_suggestions, clinical_text):
    """Cross-reference AI suggestions against the CDT dataset.
    Enriches each suggestion with validated fees, denial risks, and a match flag.
    Adjusts confidence down when denial risk factors are present that the note
    does not clearly address."""
    clinical_lower = clinical_text.lower()

    for suggestion in ai_suggestions:
        code = suggestion.get("code", "")
        ref = CDT_CODES.get(code)
        if ref:
            suggestion["verified"] = True
            suggestion["reference_fee"] = ref["typical_fee"]
            suggestion["denial_risk_factors"] = ref["denial_risk_factors"]
            suggestion["category"] = ref["category"]

            # Penalize confidence for each unaddressed denial risk factor
            score = suggestion.get("confidence_score", 90)
            for risk in ref["denial_risk_factors"]:
                risk_keywords = risk.lower().split()
                # Check if the clinical note addresses this risk
                addressed = sum(1 for kw in risk_keywords if kw in clinical_lower)
                if addressed < len(risk_keywords) * 0.4:
                    score = max(score - 12, 30)
            suggestion["confidence_score"] = score
        else:
            suggestion["verified"] = False
            suggestion["reference_fee"] = None
            suggestion["denial_risk_factors"] = ["Code not found in CDT reference — verify manually"]
            suggestion["category"] = "Unknown"
            suggestion["confidence_score"] = max(
                suggestion.get("confidence_score", 50) - 20, 20
            )
    return ai_suggestions


def build_cdt_reference_block():
    """Format CDT codes as text for injection into the system prompt."""
    lines = ["Available CDT codes (use ONLY these codes):"]
    for code, entry in CDT_CODES.items():
        lines.append(
            f"  {code} | {entry['category']} | {entry['description']} | typical fee: ${entry['typical_fee']}"
        )
    return "\n".join(lines)


class ClinicalNote(BaseModel):
    text: str


@app.post("/api/analyze-note")
async def analyze_clinical_note(note: ClinicalNote):
    try:
        # Mocking the PII scrubber for the MVP narrative
        print("SIMULATED STEP: Scrubbing PII (Names, DOBs) using Presidio-Analyzer before sending to LLM...")

        cdt_reference = build_cdt_reference_block()

        system_prompt = f"""You are an expert dental billing specialist for endodontics.
Analyze the following clinical note and extract the exact CDT codes that apply.

{cdt_reference}

For each code you suggest, provide:
- A confidence_score (0-100) reflecting the likelihood this claim will be APPROVED by the insurance company. Factor in: whether the clinical note contains sufficient detail, whether medical necessity is clearly established, whether required documentation (radiographs, measurements, pre-authorization) is mentioned, and whether common insurance company denial triggers are addressed. Be conservative — only score above 90 if the documentation is truly bulletproof.
- Step-by-step reasoning explaining why the code applies AND any documentation gaps
- Any denial risk factors specific to this case

Respond ONLY in valid JSON with this structure:
{{
    "suggested_codes": [
        {{
            "code": "D3330",
            "description": "Root canal - molar",
            "fee_estimate": 950,
            "confidence_score": 95,
            "reasoning": "Step-by-step explanation of why this code was chosen."
        }}
    ],
    "total_estimated_value": 950,
    "denial_risks": ["List any missing info that could trigger a denial"],
    "status": "Ready to File"
}}

Set status to "Clarification Needed" if any confidence_score is below 85."""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": f"Here is the clinical note:\n\n{note.text}"
                }
            ]
        })

        # Calling Claude on Bedrock
        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-sonnet-4-20250514-v1:0',
            contentType='application/json',
            accept='application/json',
            body=body
        )

        response_body = json.loads(response.get('body').read())
        ai_response_text = response_body['content'][0]['text']

        # Strip markdown code fences if Claude wraps the JSON in ```json ... ```
        cleaned = ai_response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]

        result = json.loads(cleaned)

        # Cross-reference AI output against CDT dataset
        result["suggested_codes"] = match_cdt_codes(result.get("suggested_codes", []), note.text)

        # Recalculate status based on adjusted confidence scores
        min_confidence = min(
            (c.get("confidence_score", 100) for c in result["suggested_codes"]),
            default=100
        )
        if min_confidence < 85:
            result["status"] = "Clarification Needed"

        return result

    except Exception as e:
        print(f"AWS Bedrock Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "Backend is running!"}