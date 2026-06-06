# 🔍 Fine Print

**Fine Print** reads the Terms & Conditions so you don't have to.

Paste a T&C URL or raw text and instantly get a plain-English breakdown of what you're actually agreeing to — with red flags highlighted.

## What it does

- Fetches and parses any Terms & Conditions page from a URL
- Runs a 2-agent GraphN pipeline to detect risky clauses across 7 categories: data privacy, billing, content ownership, account termination, legal rights, surveillance, and indemnification
- Returns a risk score out of 10, a plain-English summary, and colour-coded red/yellow/green flags

## Tech stack

- **Streamlit** — frontend
- **GraphN** — multi-agent AI pipeline (TC_Analyzer + Report_Synthesizer)
- **Lightning AI Studios** — hosting

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Create a `.env` file in the project root with the following:

```
GRAPHN_API_KEY=your_graphn_api_key
GRAPHN_WORKSPACE=your_workspace_id
GRAPHN_WORKFLOW_ID=your_workflow_id
GRAPHN_URL=https://cp.graphn.ai
```

## Deploying on Lightning AI Studios

Upload `app.py` and `requirements.txt` to your Studio, then add the following as **Secrets** in the Studio settings (do not upload your `.env` file):

| Secret | Value |
|---|---|
| `GRAPHN_API_KEY` | Your GraphN API key |
| `GRAPHN_WORKSPACE` | Your GraphN workspace ID |
| `GRAPHN_WORKFLOW_ID` | Your GraphN workflow ID |
| `GRAPHN_URL` | `https://cp.graphn.ai` |

Then run:

```bash
pip install -r requirements.txt
streamlit run app.py
```
