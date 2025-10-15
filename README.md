# DPP‑Comply MVP (Local Development)

Local demo showing a Digital Product Passport (DPP) pipeline aligned to ESPR concepts.
Runs entirely offline in mock mode and demonstrates:
- FastAPI backend with CORS, templating, and static serving
- AI/ML processor with **mock LLM** and rule‑based extraction (OpenAI has been added/ Add your API key in .env)
- Local RAG simulation against tiny regulatory snippets
- ESPR‑flavored data structures and a basic compliance report
- Responsive, accessible frontend (vanilla HTML/CSS/JS)
- Local file persistence and ready‑made tests

## Quick Start

# Environment template
IN PROJECT STRUCTURE MAKE SURE TO ADD( .env in project ):
- ENV=development
- MOCK_MODE=true
- AI_BACKEND=openai
- OPENAI_API_KEY= PLACE HERE YOUR OPEN AI KEY
- DATA_DIR=data
- ALLOW_ORIGINS=http://localhost:8000,http://127.0.0.1:8000


```bash
# 1) Create venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Setup local data
python scripts/setup_env.py

# 4) Run in dev (hot reload)
python scripts/run_dev.py
# or: uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# 5) Open app
# http://localhost:8000
```

## Environment

Copy `.env.example` to `.env` and adjust as needed.
Defaults are **mock** (no external keys). To try OpenAI, set `AI_BACKEND=openai` and provide `OPENAI_API_KEY`.

## Project Layout

```
dpp-comply-mvp/
├── backend/
│   ├── app.py
│   ├── ai_processor.py
│   ├── models.py
│   ├── config.py
│   └── services/
│       ├── supply_chain_api.py
│       └── data_validator.py
├── frontend/
│   ├── templates/
│   │   ├── index.html
│   │   └── dpp_viewer.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── data/
│   ├── raw_supplier_data/
│   ├── processed_dpp/
│   └── regulatory_docs/
├── tests/
│   ├── test_ai_processor.py
│   └── test_api_endpoints.py
├── scripts/
│   ├── setup_env.py
│   └── run_dev.py
├── .env.example
├── requirements.txt
├── package.json
└── README.md
```

## Scenarios

- **Textile Product**: Use the *Load Textile Sample* button and click *Process to DPP*.
- **Electronics Product**: Use the *Load Electronics Sample* button and click *Process to DPP*.

Each processed product is saved to `data/processed_dpp/{product_id}.json`. View via *DPP Viewer* link.

## Testing

```bash
pytest tests/ -v
```

## 📸 Screenshots

| Feature | Preview |
|--------|---------|
| Output | ![OUTPUT](Outputs\Output.png)
| Saved DPP | ![SAVED_DPP](Outputs\Savedruns.png) | 

## Explain extensibility

Integrating with real supply-chain APIs later 

Store DPPs in a cloud database

Use Large Hugging Face LLMs for intelligent parsing

Connect to EU ESPR sandbox API when available

## Notes

- This MVP keeps the ESPR lens without claiming official compliance.
- The compliance report is illustrative and can be extended with real rules.
- The mock RAG uses tiny local text files under `data/regulatory_docs/`.
