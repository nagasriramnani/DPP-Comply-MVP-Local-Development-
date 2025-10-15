import json
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, Request, UploadFile, File, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .ai_processor import standardize_product_data
from .models import DigitalProductPassport
from .services.data_validator import check_espr_compliance

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw_supplier_data"
PROCESSED_DIR = DATA_DIR / "processed_dpp"

app = FastAPI(title="DPP-Comply MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and templates
STATIC_DIR = ROOT_DIR / "frontend" / "static"
TEMPLATES_DIR = ROOT_DIR / "frontend" / "templates"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Ensure data directories
for d in (DATA_DIR, RAW_DIR, PROCESSED_DIR):
    d.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dpp/{product_id}", response_class=HTMLResponse)
def dpp_viewer(request: Request, product_id: str):
    return templates.TemplateResponse("dpp_viewer.html", {"request": request, "product_id": product_id})


@app.post("/api/process-product")
async def process_product(raw: Dict[str, Any] = Body(...)):
    """
    Ingest raw supplier data (possibly messy/unstructured) and produce a standardized DPP.
    Saves raw input and processed DPP to local filesystem for demo purposes.
    """
    product_id = raw.get("product_id") or str(uuid.uuid4())
    raw_path = RAW_DIR / f"{product_id}.json"
    with raw_path.open("w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    # Process via AI/Rule-based pipeline
    try:
        dpp: DigitalProductPassport = standardize_product_data(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Processing error: {e}")

    processed_path = PROCESSED_DIR / f"{dpp.product_id}.json"
    with processed_path.open("w", encoding="utf-8") as f:
        json.dump(dpp.model_dump(), f, indent=2, ensure_ascii=False)

    return {"message": "processed", "product_id": dpp.product_id, "dpp": dpp.model_dump()}


@app.get("/api/products/")
def list_products():
    items = []
    for fp in PROCESSED_DIR.glob("*.json"):
        try:
            with fp.open("r", encoding="utf-8") as f:
                data = json.load(f)
                items.append({"product_id": data.get("product_id"), "product_name": data.get("product_name")})
        except Exception:
            continue
    return {"products": items}


@app.get("/api/product/{product_id}/dpp")
def get_dpp(product_id: str):
    fp = PROCESSED_DIR / f"{product_id}.json"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="DPP not found")
    with fp.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@app.get("/api/product/{product_id}/compliance-report")
def compliance_report(product_id: str):
    fp = PROCESSED_DIR / f"{product_id}.json"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="DPP not found")
    with fp.open("r", encoding="utf-8") as f:
        data = json.load(f)
    report = check_espr_compliance(data)
    return report
