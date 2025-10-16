import os
import re
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Tuple

from .config import settings
from .models import DigitalProductPassport, Material

# Optional OpenAI import guarded
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DOCS_DIR = DATA_DIR / "regulatory_docs"

def _load_regulatory_snippets() -> List[Tuple[str, str]]:
    snippets = []
    if DOCS_DIR.exists():
        for fp in DOCS_DIR.glob("*.txt"):
            with fp.open("r", encoding="utf-8") as f:
                snippets.append((fp.stem, f.read()))
    else:
        snippets = [
            ("ESPR_Article_1", "Products must contain clear material composition and recycled content."),
            ("ESPR_Article_2", "CO2 footprint reporting should be provided in kg CO2e with methodology."),
            ("ESPR_Article_3", "Provide repairability and end-of-life recycling instructions."),
        ]
    return snippets

RAG_STORE = _load_regulatory_snippets()

def _mock_llm_summarize(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:220] + "...") if len(text) > 220 else text

def _extract_materials(unstructured: str) -> List[Material]:
    mats = []
    for name, pct in re.findall(r"([A-Za-z ]+?)\s*(\d{1,3})\s*%", unstructured):
        name = name.strip().lower().title()
        try:
            value = float(pct)
            if 0 <= value <= 100:
                mats.append(Material(name=name, percentage=value))
        except ValueError:
            continue
    if not mats:
        keywords = ["Cotton", "Polyester", "Nylon", "Wool", "Steel", "Aluminium", "Glass", "ABS", "Copper"]
        for kw in keywords:
            if kw.lower() in unstructured.lower():
                mats.append(Material(name=kw, percentage=0.0))
    total = sum(m.percentage for m in mats)
    if total > 0 and 80 <= total <= 120:
        for m in mats:
            m.percentage = round(m.percentage / total * 100.0, 2)
    return mats[:10]

def _parse_recycled_content(text: str) -> float:
    m = re.search(r"(recycled|post-consumer).{0,10}?(\d{1,3})\s*%", text, re.I)
    if m:
        try:
            val = float(m.group(2))
            return max(0.0, min(val, 100.0))
        except Exception:
            pass
    return 0.0

def _parse_co2(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg\s*CO2e?|CO2)", text, re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    m2 = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
    if m2:
        try:
            return float(m2.group(1))
        except Exception:
            pass
    return 0.0

def _find_references(text: str) -> List[str]:
    refs = []
    for art_id, snippet in RAG_STORE:
        if any(kw.lower() in text.lower() for kw in ["material", "recycled", "co2", "repair", "recycling"]):
            if "material" in text.lower() and "material" in snippet.lower(): refs.append(art_id)
            if "recycled" in text.lower() and "recycled" in snippet.lower(): refs.append(art_id)
            if "co2" in text.lower() and "co2" in snippet.lower(): refs.append(art_id)
            if "repair" in text.lower() and "repair" in snippet.lower(): refs.append(art_id)
            if "recycling" in text.lower() and "recycling" in snippet.lower(): refs.append(art_id)
    return sorted(list(set(refs)))[:5]

def _openai_assisted_standardize(raw: Dict[str, Any]) -> Dict[str, Any]:
    if OpenAI is None or not settings.OPENAI_API_KEY:
        return {}
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = f"""You are standardizing a Digital Product Passport from messy supplier data.
Return a strict JSON object with keys: product_id, product_name, manufacturer, materials_composition (list of {{name, percentage}}),
recycled_content_percentage, co2_footprint_kg, repair_score, recycling_instructions, supply_chain_partners (list of strings),
compliance_status, espr_article_references (list of strings).

Messy data:
{json.dumps(raw)}

If a value is missing, infer conservatively and explain minimal assumptions in a hidden field 'notes'."""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = resp.choices[0].message.content  # type: ignore
        match = re.search(r"{.*}", content, re.S)
        if match:
            data = json.loads(match.group(0))
            data.pop("notes", None)
            return data
    except Exception:
        pass
    return {}

def standardize_product_data(raw: Dict[str, Any]) -> DigitalProductPassport:
    unstructured_parts = []
    for k in ("description", "notes", "bom_text", "specs", "details"):
        val = raw.get(k)
        if isinstance(val, str):
            unstructured_parts.append(val)
    unstructured = "\n".join(unstructured_parts)

    data = {}
    if settings.AI_BACKEND == "openai":
        data = _openai_assisted_standardize(raw)

    if not data:
        materials = _extract_materials(unstructured)
        recycled_pct = _parse_recycled_content(unstructured)
        co2 = _parse_co2(unstructured)
        refs = _find_references(unstructured if unstructured else "material recycled co2 repair recycling")

        product_id = raw.get("product_id") or str(uuid.uuid4())
        product_name = raw.get("product_name") or raw.get("name") or "Unknown Product"
        manufacturer = raw.get("manufacturer") or raw.get("brand") or "Unknown Manufacturer"
        repair_score = raw.get("repair_score") or "N/A"
        recycling_instructions = raw.get("recycling_instructions") or "Check local guidelines; disassemble by material where possible."
        supply_chain = raw.get("supply_chain_partners") or raw.get("suppliers") or []

        data = {
            "product_id": product_id,
            "product_name": product_name,
            "manufacturer": manufacturer,
            "materials_composition": [m.model_dump() for m in materials],
            "recycled_content_percentage": recycled_pct,
            "co2_footprint_kg": co2,
            "repair_score": str(repair_score),
            "recycling_instructions": recycling_instructions,
            "supply_chain_partners": supply_chain,
            "compliance_status": "unknown",
            "espr_article_references": refs or ["ESPR_Article_1", "ESPR_Article_2"],
        }

    return DigitalProductPassport(**data)

# ---------- New helpers: Insights + QA ----------

def _compose_summary_rules(dpp: Dict[str, Any]) -> str:
    mats = dpp.get("materials_composition") or []
    top_mats = ", ".join(f"{m.get('name','?')} {m.get('percentage',0)}%" for m in mats[:4]) or "not specified"
    recycled = dpp.get("recycled_content_percentage", 0.0)
    co2 = dpp.get("co2_footprint_kg", 0.0)
    repair = dpp.get("repair_score", "N/A")
    status = dpp.get("compliance_status", "unknown")

    hints = []
    if recycled < 20:
        hints.append("Recycled content below typical targets (≥20–30%). Consider supplier update.")
    if co2 == 0:
        hints.append("CO₂ footprint not reported; add methodology and kg CO₂e.")
    if repair in ("N/A", "", None):
        hints.append("Repair score missing; include iFixit-style or internal metric.")
    if not dpp.get("recycling_instructions"):
        hints.append("Add clear end-of-life recycling guidance.")

    bullets = "\n".join([f"- {h}" for h in hints]) or "- No immediate issues detected."
    return (
        f"Product: {dpp.get('product_name','Unknown')} (Manufacturer: {dpp.get('manufacturer','Unknown')})\n"
        f"Materials: {top_mats}\n"
        f"Recycled content: {recycled:.1f}%\n"
        f"CO₂ footprint: {co2:.2f} kg CO₂e\n"
        f"Repair score: {repair}\n"
        f"Compliance status: {status}\n\n"
        f"Recommendations:\n{bullets}"
    )

def summarize_insights(dpp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a dict with short 'summary' text and a risk/compliance 'score' 0..100.
    Uses OpenAI if configured else rule-based.
    """
    if settings.AI_BACKEND == "openai" and OpenAI and settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = (
                "Generate a concise compliance-oriented summary and a 0..100 score for this Digital Product Passport.\n"
                "Return JSON with keys: summary (string, 4-6 sentences), score (number 0..100).\n\n"
                f"DPP JSON:\n{json.dumps(dpp)}"
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = resp.choices[0].message.content  # type: ignore
            match = re.search(r"{.*}", content, re.S)
            if match:
                out = json.loads(match.group(0))
                if "summary" in out and "score" in out:
                    return out
        except Exception:
            pass

    # Rule-based fallback
    text = _compose_summary_rules(dpp)
    # crude scoring
    score = 70.0
    if dpp.get("recycled_content_percentage", 0.0) < 20: score -= 10
    if dpp.get("co2_footprint_kg", 0.0) == 0: score -= 10
    if not dpp.get("recycling_instructions"): score -= 10
    return {"summary": text, "score": max(0, min(100, score))}

def qa_on_dpp(dpp: Dict[str, Any], question: str) -> str:
    """
    Answers a user question about the current product DPP.
    Uses OpenAI if configured else rule-based template.
    """
    if settings.AI_BACKEND == "openai" and OpenAI and settings.OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = (
                "Answer the question using ONLY the provided DPP JSON context. "
                "If unknown, say so briefly. Keep answer under 6 sentences.\n\n"
                f"DPP:\n{json.dumps(dpp)}\n\n"
                f"Question: {question}"
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()  # type: ignore
        except Exception:
            pass

    # Rule-based fallback
    mats = ", ".join(f"{m.get('name')} {m.get('percentage',0)}%" for m in dpp.get("materials_composition", [])) or "not specified"
    recycled = dpp.get("recycled_content_percentage", 0.0)
    co2 = dpp.get("co2_footprint_kg", 0.0)
    if "recycle" in question.lower():
        return f"Recycling guidance: {dpp.get('recycling_instructions','not provided')}. Materials: {mats}."
    if "co2" in question.lower() or "footprint" in question.lower():
        return f"Reported CO₂ footprint: {co2} kg CO₂e."
    if "materials" in question.lower() or "composition" in question.lower():
        return f"Materials composition: {mats}."
    if "recycled" in question.lower():
        return f"Recycled content: {recycled:.1f}%."
    return "Based on the DPP, the requested detail isn't explicitly reported. Consider updating supplier data."
