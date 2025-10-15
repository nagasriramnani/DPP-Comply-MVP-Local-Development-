import os, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw_supplier_data"
PROC = DATA / "processed_dpp"
DOCS = DATA / "regulatory_docs"

for d in (DATA, RAW, PROC, DOCS):
    d.mkdir(parents=True, exist_ok=True)

# create a couple of tiny regulatory snippets
(DOCS / "ESPR_Article_1.txt").write_text("Products must contain clear material composition and recycled content.", encoding="utf-8")
(DOCS / "ESPR_Article_2.txt").write_text("CO2 footprint reporting should be provided in kg CO2e with methodology.", encoding="utf-8")
(DOCS / "ESPR_Article_3.txt").write_text("Provide repairability and end-of-life recycling instructions.", encoding="utf-8")

print("Environment ready. Data directories created.")
