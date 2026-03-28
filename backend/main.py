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


# Words to filter when matching risk factors — these describe the absence/policy,
# not clinical evidence terms we'd find in a well-documented note
_RISK_FILTER_WORDS = frozenset({
    'missing', 'requires', 'required', 'not', 'no', 'lacks', 'without',
    'exceeds', 'often', 'needed', 'if', 'may', 'can', 'done', 'same',
    'day', 'first', 'per', 'some', 'for', 'with', 'the', 'a', 'an',
    'and', 'or', 'of', 'in', 'on', 'to', 'is',
    'insurance', 'company', 'payable', 'bundled', 'limits', 'frequency',
    'pre-authorization', 'pre-auth', 'authorization',
})


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
                # Extract only clinical evidence terms, ignoring qualifiers
                risk_keywords = [w for w in risk.lower().split()
                                 if w not in _RISK_FILTER_WORDS and len(w) > 2]
                if not risk_keywords:
                    continue
                addressed = sum(1 for kw in risk_keywords if kw in clinical_lower)
                if addressed < max(len(risk_keywords) * 0.5, 1):
                    score = max(score - 8, 45)
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


class ClaimRequest(BaseModel):
    text: str
    insurance_company: str = "General"


@app.post("/api/analyze-note")
async def analyze_clinical_note(request: ClaimRequest):
    try:
        print("SIMULATED STEP: Scrubbing PII (Names, DOBs) using Presidio-Analyzer before sending to LLM...")

        cdt_reference = build_cdt_reference_block()

        system_prompt = f"""You are Claim Helper, an autonomous Revenue Cycle Management (RCM) AI agent.
You have master-level expertise in US dental and medical billing: ADA CDT coding, AMA CPT coding,
WHO ICD-10-CM diagnostic coding, and commercial insurance adjudication algorithms.

The patient's insurance company is: {request.insurance_company}

{cdt_reference}

INSTRUCTIONS — execute each step systematically:

STEP 1: CDT Code Extraction
Analyze the clinical note and identify the correct CDT codes from the reference list above.
For each code, estimate the fee based on the reference data.

STEP 2: Cross-Coding (Medical Codes)
If the procedure has medical implications (surgery, trauma, pathology, complex diagnosis),
identify the corresponding CPT and ICD-10-CM codes needed to bill medical insurance.
Return empty lists if cross-coding does not apply.

STEP 3: Risk Assessment
Evaluate the claim against insurance adjudication criteria for {request.insurance_company}.
Give an accurate, balanced assessment — predict the REAL outcome, not the worst case.

Apply denial codes ONLY when clearly warranted:
- CO-50 (Lack of Medical Necessity): The note fundamentally fails to justify why the procedure
  was clinically necessary — missing specific diagnosis, severity indicators, objective findings,
  or rationale for why conservative alternatives were insufficient.
  Do NOT flag CO-50 if the note documents clear pathology, symptoms, clinical findings, and
  radiographic evidence supporting the procedure.
- CO-11 (Diagnosis/Procedure Mismatch): There is a genuine logical disconnect between the
  documented condition and the procedure performed (e.g., billing surgical extraction but
  documenting only a simple extraction).
  Do NOT flag CO-11 for minor documentation gaps.
- CO-16 (Missing Information for Unlisted Code): Flag ONLY when an unlisted/by-report procedure
  code (e.g., CPT 41899) is used without detailed justification, OR when truly critical required
  information is completely absent (no tooth number at all, no procedure description at all).
  General documentation improvements do NOT warrant CO-16.

adjudication_status:
- "APPROVED" — Documentation adequately supports the procedures. Use this for well-documented
  notes with clear pathology, clinical findings, and procedure details — even if minor
  improvements could be made. This is the expected result for thorough clinical documentation.
- "HIGH_DENIAL_RISK" — Documentation has a significant, specific deficiency likely to trigger
  an automated denial. Reserve for genuinely problematic claims where key evidence is absent.

denial_risk_code: The most relevant code if HIGH_DENIAL_RISK, otherwise null.

STEP 4: Medical Necessity Narrative
ALWAYS generate a medical_necessity_narrative — never return null for this field.
- For APPROVED claims: Write a strong clinical narrative reinforcing medical necessity using
  specific data from the note. This will be proactively attached to the claim as defense.
- For HIGH_DENIAL_RISK claims: Write the best possible narrative using available data, and
  note what additional documentation the provider should supply.
Use the tone of a specialist writing to a peer medical director. Be concise and clinical.

STEP 5: Confidence Scoring
Score each code 0-100 on likelihood of insurance approval for {request.insurance_company}.
Be conservative — only score above 90 for truly bulletproof documentation.
But also be fair — well-documented procedures with clear clinical justification should score 75-90.

OUTPUT FORMAT — respond with ONLY this JSON, no markdown, no explanation:
{{
    "adjudication_status": "APPROVED or HIGH_DENIAL_RISK",
    "denial_risk_code": null or "CO-50" or "CO-11" or "CO-16",
    "suggested_codes": [
        {{
            "code": "D3330",
            "description": "Root canal - molar",
            "fee_estimate": 950,
            "confidence_score": 85,
            "reasoning": "Step-by-step explanation"
        }}
    ],
    "cross_codes": {{
        "CPT": [],
        "ICD_10": []
    }},
    "total_estimated_value": 950,
    "denial_risks": ["list specific risks, or empty list if none"],
    "medical_necessity_narrative": "Always provide a clinical narrative here — never null",
    "status": "Ready to File or Clarification Needed"
}}"""

        user_input = json.dumps({
            "insurance_company": request.insurance_company,
            "clinical_note": request.text
        })

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        })

        response = bedrock_runtime.invoke_model(
            modelId='us.anthropic.claude-sonnet-4-20250514-v1:0',
            contentType='application/json',
            accept='application/json',
            body=body
        )

        response_body = json.loads(response.get('body').read())
        ai_response_text = response_body['content'][0]['text']

        # Strip markdown code fences if present
        cleaned = ai_response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]

        result = json.loads(cleaned)

        # Cross-reference AI output against CDT dataset
        result["suggested_codes"] = match_cdt_codes(result.get("suggested_codes", []), request.text)

        # Sort codes by confidence (highest first)
        result["suggested_codes"].sort(
            key=lambda c: c.get("confidence_score", 0), reverse=True
        )

        # Recalculate status based on adjusted confidence scores
        min_confidence = min(
            (c.get("confidence_score", 100) for c in result["suggested_codes"]),
            default=100
        )
        if min_confidence < 70:
            result["status"] = "Clarification Needed"
        if result.get("adjudication_status") == "HIGH_DENIAL_RISK":
            result["status"] = "Clarification Needed"

        return result

    except Exception as e:
        print(f"AWS Bedrock Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "Backend is running!"}