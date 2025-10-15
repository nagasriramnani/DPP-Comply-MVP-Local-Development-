# Placeholder stubs for supply chain API integration
from typing import List, Dict

def get_suppliers(product_id: str) -> List[Dict]:
    # Mocked data
    return [
        {"name": "Acme Textiles Ltd", "country": "PT", "role": "fabric"},
        {"name": "EcoPack Co", "country": "DE", "role": "packaging"},
    ]

def get_traceability_record(product_id: str) -> Dict:
    return {
        "product_id": product_id,
        "chain_of_custody": ["Supplier A", "Supplier B", "Warehouse", "Retail"],
        "last_updated": "2025-01-12",
    }
