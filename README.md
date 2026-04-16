# AI IT Support Agent

A mock IT admin panel with an AI agent that interprets natural-language support requests and carries them out through browser automation.

## What It Does

The system demonstrates an IT support workflow where a user can type requests like:

- "create a new user named Jane Doe"
- "deactivate sarah@company.com"
- "delete john@company.com"

The agent parses the request, builds a plan, and then uses browser automation to interact with the admin UI like a human.

## Project Structure

- `backend/admin.py` - FastAPI backend for the mock admin panel
- `frontend/` - HTML, CSS, and JavaScript for the UI
- `backend/bru.py` - browser automation prototype
- `backend/bru_gemini.py` - Gemini-based browser agent prototype
- `backend/agent_pipeline.py` - planner-executor-verifier agent pipeline

## Features

- Mock IT admin panel
- Create user flow
- Toggle user status
- Delete user flow
- AI parsing of natural-language requests
- Planner-executor-verifier architecture
- Optional approval for destructive actions

## Tech Stack

- Python
- FastAPI
- Pydantic
- OpenAI-compatible API
- Browser Use / browser-use-sdk
- HTML, CSS, JavaScript

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate it

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If required, install these explicitly:

```bash
pip install python-dotenv pydantic openai fastapi uvicorn browser-use browser-use-sdk langchain-openai
```

## Environment Variables

Create a `.env` file in the project root:

```env
GITHUB_TOKEN=your_github_models_token
BROWSER_USE_API_KEY=bu_your_browser_use_key
GEMINI_API_KEY=your_gemini_key
```

## Run the App

Run each service in a separate terminal.

### 1. Start backend API

```bash
cd backend
uvicorn admin:app --reload --port 8000
```

### 2. Start frontend

```bash
cd frontend
python -m http.server 3000
```

### 3. Run the agent

Planner/Executor/Verifier pipeline:

```bash
python backend/agent_pipeline.py
```

Alternative prototypes:

```bash
python backend/bru.py
python backend/bru_gemini.py
```

## Example Requests

- create a new user named Jane Doe, email jane.doe@company.com, role Engineer, department Engineering
- deactivate sarah@company.com
- delete john@company.com
- reset password for mike@company.com

## Architecture

1. Parser extracts intent and fields from user text.
2. Planner converts the request into structured steps.
3. Executor runs browser automation on the admin UI.
4. Verifier checks outcomes and can trigger retries.

## Notes

- This is a demo/mock IT panel and agent.
- Browser-based execution simulates real operator behavior via UI actions.
- Cloud browser providers may not reach `localhost`; use a tunnel URL if needed.

## License

Demo and educational use.