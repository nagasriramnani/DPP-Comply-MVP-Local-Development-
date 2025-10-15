import os
import re
import json
import uuid  
from pathlib import Path
from typing import Dict, Any, List, Tuple

from .config import settings
from .models import DigitalProductPassport, Material

# Optional OpenAI import guarded for environments without the package or API key
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DOCS_DIR = DATA_DIR / "regulatory_docs"

def _load_regulatory_snippets() -> List[Tuple[str, str]]:
    """
    Simulated RAG store: load small local text snippets and return [(id, text)]
    """
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
    # extremely simple mock summarizer
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:220] + "...") if len(text) > 220 else text

def _extract_materials(unstructured: str) -> List[Material]:
    # Rule-based extraction of "material: xx%" pairs or keywords
    mats = []
    # Look for patterns like "Cotton 60%, Polyester 40%"
    for name, pct in re.findall(r"([A-Za-z ]+?)\s*(\d{1,3})\s*%", unstructured):
        name = name.strip().lower().title()
        try:
            value = float(pct)
            if 0 <= value <= 100:
                mats.append(Material(name=name, percentage=value))
        except ValueError:
            continue
    # Fallback keywords if nothing found
    if not mats:
        keywords = ["Cotton", "Polyester", "Nylon", "Wool", "Steel", "Aluminium", "Glass", "ABS", "Copper"]
        for kw in keywords:
            if kw.lower() in unstructured.lower():
                mats.append(Material(name=kw, percentage=0.0))
    # Normalize percentages to sum to 100 if totals are close
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
    # find numbers with kg
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg\s*CO2e?|CO2)", text, re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    # otherwise try a lone number and assume kg
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
            # naive: include articles relevant to keywords present
            if "material" in text.lower() and "material" in snippet.lower():
                refs.append(art_id)
            if "recycled" in text.lower() and "recycled" in snippet.lower():
                refs.append(art_id)
            if "co2" in text.lower() and "co2" in snippet.lower():
                refs.append(art_id)
            if "repair" in text.lower() and "repair" in snippet.lower():
                refs.append(art_id)
            if "recycling" in text.lower() and "recycling" in snippet.lower():
                refs.append(art_id)
    return sorted(list(set(refs)))[:5]

def _openai_assisted_standardize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Illustrative OpenAI path. Falls back to rule-based if unavailable.
    """
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
        # Using responses API for simplicity
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = resp.choices[0].message.content  # type: ignore
        # Attempt to extract JSON from the response
        match = re.search(r"{.*}", content, re.S)
        if match:
            data = json.loads(match.group(0))
            data.pop("notes", None)
            return data
    except Exception:
        pass
    return {}

def standardize_product_data(raw: Dict[str, Any]) -> DigitalProductPassport:
    """
    Primary entrypoint that selects between mock/rule-based and OpenAI-assisted processing.
    """
    # Concatenate possible unstructured fields
    unstructured_parts = []
    for k in ("description", "notes", "bom_text", "specs", "details"):
        val = raw.get(k)
        if isinstance(val, str):
            unstructured_parts.append(val)
    unstructured = "\n".join(unstructured_parts)

    # Try OpenAI path if configured
    data = {}
    if settings.AI_BACKEND == "openai":
        data = _openai_assisted_standardize(raw)

    # Fallback to rule-based mock
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
