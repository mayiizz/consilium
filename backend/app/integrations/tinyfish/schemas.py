from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TinyFishSearchHit(BaseModel):
    title: str = ""
    url: str = ""
    snippet: str = ""
    site_name: str = ""
    position: int = 0


class TinyFishSearchResponse(BaseModel):
    query: str = ""
    results: List[TinyFishSearchHit] = Field(default_factory=list)
    total_results: int = 0
    page: int = 0


class TinyFishRunResult(BaseModel):
    run_id: Optional[str] = None
    status: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    url: str = ""
    goal: str = ""


class ResearchSourceRecord(BaseModel):
    url: str
    title: str = ""
    extraction_method: str = "tinyfish"
    extracted_content: str = ""
    extracted_data: Optional[Dict[str, Any]] = None
    source_type: str = "website"
    verification_status: str = "partially_verified"
    retrieved_at: datetime
    error: Optional[str] = None
