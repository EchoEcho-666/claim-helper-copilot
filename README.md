# Claim Copilot

An AI-powered clinical note analyzer built for TDO Software, American Data and Marea to automate CDT coding and flag insurance denial risks before claim submission.

## Tech Stack
* **Frontend:** React.js 
* **Backend:** Python, FastAPI
* **AI Model:** Anthropic Claude 3 (via AWS Bedrock)

## Security & Architecture Note
For security best practices, no AWS credentials or API keys are in this repository. The `boto3` client is configured to inherit credentials dynamically from the host machine's secure `~/.aws/credentials` file or environment variables.

## How to Run Locally
1. Clone the repo.
2. Ensure you have valid AWS credentials configured locally with Bedrock access.
3. Run the backend: `cd backend && uvicorn main:app --reload`
4. Run the frontend: `cd frontend && npm start`