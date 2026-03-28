# Claim Helper Copilot

An AI-powered clinical note analyzer built for **TDO Software**, **American Data**, and **Marea** (Fluent Software Group) to automate CDT coding and flag insurance denial risks **before** claim submission.

---

## What It Does

A dentist finishes a procedure and types (or dictates) a clinical note. Claim Copilot reads that note instantly, suggests the correct billing codes, scores its own confidence, flags anything an insurance company would use to deny the claim, and explains its reasoning — all before the patient leaves the chair.

---

## Key Concepts & Terminology

### CDT Codes (Current Dental Terminology)

CDT codes are standardized 5-character codes maintained by the **American Dental Association (ADA)** that describe dental procedures. They always start with the letter "D".

| Code | Meaning |
|------|---------|
| D3310 | Root canal therapy — anterior tooth |
| D3330 | Root canal therapy — molar tooth |
| D2740 | Full-coverage ceramic crown |
| D0220 | Periapical radiograph (X-ray) |
| D9110 | Palliative (emergency) pain treatment |

CDT codes describe **what was done**. Dental insurance pays based on these codes, typically under a capped annual maximum ($1,500–$2,000/year).

### ICD-10-CM (International Classification of Diseases)

ICD-10 codes describe **why** something was done — the patient's diagnosis. They are required by medical insurance to prove "medical necessity." Example: `K04.1` = Necrosis of pulp (dead nerve in a tooth).

Dental claims historically did not require ICD-10 codes, but high-acuity procedures (oral surgery, biopsies, trauma) increasingly require **cross-coding** — billing medical insurance first with ICD-10 + CPT codes before billing dental insurance with CDT codes.

### CPT Codes (Current Procedural Terminology)

CPT codes are the medical equivalent of CDT codes, maintained by the **American Medical Association (AMA)**. Used when billing medical (not dental) insurance for procedures that cross into medical territory (e.g., `41899` = unlisted dentoalveolar procedure).

### Cross-Coding

The practice of billing a dental procedure to **medical** insurance using CPT + ICD-10 codes to exhaust medical benefits first, then billing the remainder to dental insurance via CDT. This is common for oral surgery, sleep apnea appliances, and facial trauma. Most dental practices struggle with this because clinicians are not trained in medical coding — it is a major source of revenue leakage.

### Medical Necessity

The clinical justification that a procedure was **essential**, not elective or cosmetic. Insurance companies require specific clinical language in the documentation — exact measurements, radiographic findings, quantified structural loss. Vague notes like "patient had pain, did crown" get denied.

### Common Denial Codes

| Code | Name | What It Means |
|------|------|---------------|
| **CO-50** | Medical Necessity | The clinical note does not justify why the procedure was needed. Most common denial reason. |
| **CO-11** | Diagnosis/Procedure Mismatch | The ICD-10 diagnosis does not logically support the intensity of the procedure performed. Insurance companies use this to downcode expensive procedures to cheaper ones. |
| **CO-16** | Missing Information | The claim lacks required attachments, narratives, or clinical details. Triggers automatic human audit for unlisted procedure codes. |

### Predictive Adjudication

Traditional billing is **reactive** — submit a claim, wait 30 days, find out it was denied, then scramble to appeal. Claim Copilot performs **predictive adjudication**: it simulates how an insurance company's algorithm would evaluate the claim and flags risks *before* submission, while there is still time to fix the documentation.

### Confidence Scoring

Each suggested billing code gets a confidence score (0–100%) based on how strongly the clinical note supports it. Scores below 85% trigger a "Clarification Needed" status, signaling the clinician should add more detail before filing.

### PII Scrubbing

Before sending clinical text to the AI model, personally identifiable information (patient names, dates of birth, insurance IDs) should be removed. The current MVP simulates this step; production would use a library like **Microsoft Presidio** for automated de-identification.

---

## Implemented Features (Current Version)

### Backend (`backend/main.py`)

- **CDT Reference Data Layer** — Loads `backend/data/cdt_mock.json` (15 high-frequency endodontic/diagnostic codes) at startup. The full CDT code list is injected into the AI prompt so Claude selects from real, validated codes with accurate fee schedules.

- **AI-Powered Code Extraction** — Sends the clinical note to **Claude Sonnet 4** via AWS Bedrock with a structured system prompt. Claude analyzes the note and returns suggested CDT codes, fee estimates, confidence scores, and step-by-step reasoning.

- **CDT Cross-Validation (`match_cdt_codes`)** — After Claude responds, every suggested code is cross-referenced against the CDT dataset. Each code is enriched with:
  - `verified`: whether the code exists in the CDT reference
  - `reference_fee`: the typical fee from the dataset (shown alongside the AI estimate)
  - `denial_risk_factors`: known risk factors from the dataset for that specific code
  - `category`: procedure category (Diagnostic, Endodontics, Restorative, etc.)

- **Markdown Fence Stripping** — Handles cases where the LLM wraps JSON output in markdown code blocks, preventing parse failures.

- **Simulated PII Scrubbing** — Logs a simulated Presidio-based PII scrub step before sending data to the LLM.

- **Health Check Endpoint** — `GET /health` for uptime monitoring.

### Frontend (`frontend/src/App.js`)

- **Clinical Note Input** — Free-text area for pasting or typing clinical notes, pre-loaded with a sample endodontic note.

- **Per-Code Confidence Bars** — Each suggested code displays a color-coded progress bar:
  - Green (85%+): strong clinical support
  - Yellow (60–84%): moderate — may need additional documentation
  - Red (<60%): weak — high denial risk

- **CDT Verified / Unverified Badges** — Each code shows whether it was found in the CDT reference dataset. "Unverified" codes should be manually checked before filing.

- **Reference Fee Comparison** — When the AI's fee estimate differs from the CDT dataset's typical fee, both values are shown side-by-side so the biller can spot discrepancies.

- **Per-Code Denial Risk Factors** — Pulled from the CDT dataset (not AI-generated), these flag known reasons insurance companies deny specific codes (e.g., "missing pre-op radiograph" for root canal codes).

- **Expandable AI Reasoning** — Each code has a collapsible "AI Reasoning" section explaining step-by-step why the code was selected, giving the biller transparency into the AI's logic.

- **Global Denial Risk Summary** — An overall list of missing information or documentation gaps that could trigger claim denial across all suggested codes.

---

## CDT Code Data Notice

This prototype uses a **minimal mock dataset** (`backend/data/cdt_mock.json`) containing 15 high-frequency endodontic/diagnostic codes for development and demonstration purposes only.

**Production deployment requires:**
- ADA CDT Commercial License: https://www.ada.org/publications/cdt/licensing
- Integration with licensed CDT API or database
- Insurance company-specific fee schedule and policy rules engine

This approach demonstrates:
- Privacy-first architecture (simulated PII scrubbing, stateless design)
- Confidence scoring and denial risk flagging logic
- Clean separation of mock data layer for easy swap to licensed source

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js |
| Backend | Python, FastAPI |
| AI Model | Anthropic Claude Sonnet 4 (via AWS Bedrock inference profile) |
| CDT Data | Mock JSON dataset (15 endodontic/diagnostic codes) |

---

## Security

- **No credentials in this repository.** AWS keys are loaded from a local `.env` file that is excluded by `.gitignore` at both the backend and root levels.
- The `boto3` client reads `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` from environment variables at runtime.
- Clinical note text is sent to AWS Bedrock (Anthropic Claude) for processing. No patient data is stored by the application.

---

## How to Run Locally

**Prerequisites:** Python 3.10+, Node.js 18+, AWS account with Bedrock model access enabled for Claude.

1. **Clone the repo**
   ```bash
   git clone <repo-url> && cd claim-copilot
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn boto3 python-dotenv pydantic
   ```

3. **Configure AWS credentials** — create `backend/.env`:
   ```
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   ```

4. **Start the backend**
   ```bash
   uvicorn main:app --reload
   ```

5. **Start the frontend** (in a separate terminal)
   ```bash
   cd frontend
   npm install
   npm start
   ```

6. Open http://localhost:3000, paste a clinical note, and click **Generate Billing Codes**.

---

## Roadmap (Next from Blueprint)

- [ ] **Gold Standard system prompt** — cross-coding (CDT + CPT + ICD-10), predictive adjudication (CO-50/CO-11/CO-16), autonomous medical necessity narrative generation
- [ ] **Insurance company selection** — dropdown for insurance carrier (Delta Dental, Aetna, etc.) to enable carrier-specific denial prediction
- [ ] **Medical necessity narrative output** — auto-generated clinical narrative attachable to claim forms
- [ ] **RAG pipeline** — vector database loaded with insurance company policy manuals for grounded adjudication
- [ ] **Agentic tool use** — deterministic validation functions (e.g., `verify_ICD10_compatibility`)
