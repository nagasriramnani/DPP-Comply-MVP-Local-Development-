from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_process_product_and_fetch():
    payload = {
        "product_name": "EcoPhone X",
        "manufacturer": "CircuLab",
        "bom_text": "Frame: Aluminium 40%; Glass 30%; Plastics (ABS) 30% recycled 15%. Total CO2 18.5 kg CO2e.",
        "specs": "Repair score 6/10; Battery removable; End-of-life: return to store."
    }
    r = client.post("/api/process-product", json=payload)
    assert r.status_code == 200
    data = r.json()
    pid = data["product_id"]

    r2 = client.get(f"/api/product/{pid}/dpp")
    assert r2.status_code == 200
    dpp = r2.json()
    assert dpp["product_name"] == "EcoPhone X"

    r3 = client.get(f"/api/product/{pid}/compliance-report")
    assert r3.status_code == 200
    report = r3.json()
    assert "status" in report
