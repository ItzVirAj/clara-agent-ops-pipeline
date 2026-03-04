# Clara Agent Ops Pipeline

Automated onboarding pipeline for **Clara Answers** — an AI voice agent platform for service trade businesses such as electrical contractors, fire protection companies, HVAC providers, and sprinkler service teams.

Processes call recordings or transcripts to generate structured account memos, versioned agent configurations, and deployable Retell AI voice agent prompts.

---

# What It Does

## Pipeline A — Demo Call → v1 Agent

```text
demo call (audio or transcript)
  → ingest → transcribe (whisper) → extract (gemini 2.5 flash)
  → account memo v1 + agent spec v1 + system prompt v1
  → registered in sqlite + github issue created
````

## Pipeline B — Onboarding Call → v2 Agent

```text
onboarding call (audio or transcript)
  → ingest → transcribe → extract
  → patch v1 memo with new data
  → account memo v2 + agent spec v2 + system prompt v2
  → changelog generated → sqlite updated + github issue closed
```

---

# Tech Stack

| Layer                          | Tool                         | Cost      |
| ------------------------------ | ---------------------------- | --------- |
| Transcription                  | faster-whisper (local CPU)   | Free      |
| Extraction + Prompt Generation | Gemini 2.5 Flash API         | Free tier |
| Storage                        | Local JSON + SQLite          | Free      |
| Task Tracking                  | GitHub Issues API            | Free      |
| Orchestration                  | Python runners + n8n exports | Free      |
| Version Control                | GitHub                       | Free      |

---

# Project Structure

```text
clara-agent-ops-pipeline/
│
├── cfg/
│   ├── .env.example
│   ├── account_schema.json
│   └── agent_spec_schema.json
│
├── pipe/
│   ├── __init__.py
│   ├── utils.py
│   ├── ingest.py
│   ├── extract.py
│   ├── prmpt_gen.py
│   ├── store.py
│   ├── patch.py
│   └── task_push.py
│
├── scripts/
│   ├── run_demo.py
│   ├── run_onboard.py
│   └── run_batch.py
│
├── data/
│   ├── demo/
│   └── onboard/
│
├── outputs/
│   ├── accounts/
│   │   └── <acct_id>/
│   │       ├── v1/
│   │       │   ├── raw_transcript.txt
│   │       │   ├── memo.json
│   │       │   ├── agent_spec.json
│   │       │   └── agent_prompt.txt
│   │       ├── v2/
│   │       │   ├── raw_transcript.txt
│   │       │   ├── memo.json
│   │       │   ├── agent_spec.json
│   │       │   └── agent_prompt.txt
│   │       └── changelog.json
│   │
│   ├── acct_registry.db
│   └── batch_report.json
│
├── tests/
│   ├── test_ingest.py
│   ├── test_extract.py
│   ├── test_patch.py
│   └── test_prmpt_gen.py
│
├── wrkflw/
│   ├── demo_pipeline.json
│   ├── onboard_pipeline.json
│   └── README.md
│
├── logs/
├── requirements.txt
└── README.md
```

---

# Setup

## 1. Clone Repository

```bash
git clone https://github.com/ItzVirAj/clara-agent-ops-pipeline.git
cd clara-agent-ops-pipeline
```

## 2. Create Virtual Environment

```bash
python -m venv venv

venv\Scripts\activate
# source venv/bin/activate (Mac/Linux)
```

## 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

> First run downloads the Whisper base model (~145MB).

---

# Configure Environment

Copy the template:

```bash
copy cfg\.env.example cfg\.env
```

Edit `cfg/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GH_TOKEN=your_github_personal_access_token
GH_REPO=ItzVirAj/clara-agent-ops-pipeline

ACCT_OUT_DIR=outputs/accounts
LOG_DIR=logs
DATA_DEMO_DIR=data/demo
DATA_ONBOARD_DIR=data/onboard
```

### Get Gemini API Key

[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

### Get GitHub Token

GitHub → Settings → Developer Settings → Personal Access Tokens → Classic Token → enable `repo`.

---

# Usage

## Add Input Files

Follow this naming convention:

```text
data/demo/<prefix>_demo.txt
data/onboard/<prefix>_onboard.m4a
```

Examples:

```text
data/demo/bens_electric_demo.txt
data/onboard/bens_electric_onboard.m4a
```

---

## Run Batch Processing

```bash
python scripts/run_batch.py
```

---

## Run Single Demo Call

```bash
python scripts/run_demo.py data/demo/bens_electric_demo.txt
```

---

## Run Single Onboarding Call

```bash
python scripts/run_onboard.py data/onboard/bens_electric_onboard.m4a ACCT-XXXXXXXX
```

---

# Output Files

| File              | Description                                       |
| ----------------- | ------------------------------------------------- |
| memo.json         | Structured account memo extracted from transcript |
| agent_spec.json   | Generated Retell agent configuration              |
| agent_prompt.txt  | Deployable Clara system prompt                    |
| changelog.json    | Field-level changes between v1 and v2             |
| batch_report.json | Summary of batch processing results               |
| acct_registry.db  | SQLite registry of processed accounts             |

---

# Running Tests

```bash
python tests/test_ingest.py
python tests/test_extract.py
python tests/test_patch.py
python tests/test_prmpt_gen.py
```

---

# Retell Agent Import

Agent specs are generated for manual import.

1. Open Retell Dashboard
2. Create new agent
3. Open:

```
outputs/accounts/<acct_id>/v2/agent_prompt.txt
```

4. Paste contents into **System Prompt**

Transfer numbers are defined in:

```
agent_spec.json
```

---

# n8n Workflow Orchestration

Workflow exports are located in:

```
wrkflw/
```

| File                  | Description                |
| --------------------- | -------------------------- |
| demo_pipeline.json    | Demo call → v1 agent       |
| onboard_pipeline.json | Onboarding call → v2 agent |

### Install n8n

```bash
npm install -g n8n
n8n start
```

Open:

```
http://localhost:5678
```

Import workflow files and configure environment variables.

Without n8n, the Python runners operate fully standalone.

---

# Pipeline Architecture

```text
Raw Input (audio / transcript)
          │
          ▼
    pipe/ingest.py
    detect file type → normalize → transcribe if needed
          │
          ▼
    pipe/extract.py
    Gemini extraction → structured memo JSON
          │
          ▼
    pipe/prmpt_gen.py
    generate agent_spec.json + system prompt
          │
          ├── store.py        (SQLite registry)
          ├── task_push.py    (GitHub issue)
          └── outputs/v1
          │
          ▼
    pipe/patch.py  (Pipeline B)
    merge v2 data into v1 → generate changelog
          │
          ▼
    pipe/prmpt_gen.py
    regenerate updated agent configuration
          │
          └── outputs/v2
```

---

# Key Design Decisions

### No Hallucination Rule

The extraction model returns `null` for missing information.
All unknown values are flagged in `open_qs`.

### Versioned Outputs

v1 and v2 outputs are stored in separate directories.
Re-running the pipeline produces identical results.

### Patch Merge Logic

```
v1 null  + v2 value   → filled
v1 value + v2 change  → updated
v1 value + v2 null    → keep v1
v1 value + v2 same    → unchanged
```

### Local Transcription

Audio files are transcribed locally using **faster-whisper**.
No paid speech-to-text services are required.

---

# Known Limitations

1. **Gemini free tier limits**
   The free tier allows ~20 requests/day.

2. **Manual Retell import**
   Agent specs must currently be copied into the Retell dashboard manually.

3. **Transcription accuracy**
   The Whisper base model prioritizes CPU speed over maximum accuracy.

4. **Limited dataset**
   The assignment dataset contains a single account.

---

# Future Improvements

* Direct Retell API deployment
* Higher accuracy Whisper models
* Real-time webhook call processing
* Web dashboard for account tracking and diffs

---

# Links

Repository:
[https://github.com/ItzVirAj/clara-agent-ops-pipeline](https://github.com/ItzVirAj/clara-agent-ops-pipeline)

Issues:
[https://github.com/ItzVirAj/clara-agent-ops-pipeline/issues](https://github.com/ItzVirAj/clara-agent-ops-pipeline/issues)

Loom Demo:
*(to be added)*

