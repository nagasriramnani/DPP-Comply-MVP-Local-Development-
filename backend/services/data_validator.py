from typing import Dict, Any, List

def check_espr_compliance(dpp: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[str] = []
    warnings: List[str] = []

    materials = dpp.get("materials_composition", [])
    recycled = dpp.get("recycled_content_percentage", 0.0)
    co2 = dpp.get("co2_footprint_kg", 0.0)
    repair = dpp.get("repair_score", "N/A")
    instructions = dpp.get("recycling_instructions", "")

    if not materials:
        issues.append("Missing materials composition.")
    if recycled == 0.0:
        warnings.append("Recycled content not specified or zero.")
    if co2 == 0.0:
        warnings.append("CO2 footprint not specified.")
    if not instructions:
        issues.append("Recycling instructions required.")
    if repair in ("N/A", "", None):
        warnings.append("Repair score not provided.")

    status = "non_compliant" if issues else "partially_compliant" if warnings else "compliant"

    return {
        "product_id": dpp.get("product_id"),
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "espr_article_references": dpp.get("espr_article_references", []),
    }
