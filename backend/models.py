from typing import List, Optional
from pydantic import BaseModel, Field

class Material(BaseModel):
    name: str
    percentage: float = Field(ge=0, le=100)

class DigitalProductPassport(BaseModel):
    product_id: str
    product_name: str
    manufacturer: str
    materials_composition: List[Material] = []
    recycled_content_percentage: float = 0.0
    co2_footprint_kg: float = 0.0
    repair_score: str = "N/A"
    recycling_instructions: str = ""
    supply_chain_partners: List[str] = []
    compliance_status: str = "unknown"
    espr_article_references: List[str] = []
