from backend.ai_processor import standardize_product_data

def test_standardize_textile():
    raw = {
        "product_name": "Eco Tee",
        "manufacturer": "GreenThreads",
        "description": "Material: Cotton 60%, Polyester 40%. Recycled content ~ 25%. CO2 ~ 2.4 kg CO2e.",
        "notes": "Repair score 7/10; Wash cold; Recycle fabric."
    }
    dpp = standardize_product_data(raw)
    assert dpp.product_name == "Eco Tee"
    assert any(m.name == "Cotton" for m in dpp.materials_composition)
    assert dpp.co2_footprint_kg >= 2.3
