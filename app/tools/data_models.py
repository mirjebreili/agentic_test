from __future__ import annotations
from typing import List, Dict
from pydantic import BaseModel

class FeatureSummary(BaseModel):
    """A summary of market data features to be passed to the LLM."""
    instrument: str
    timeframe: str
    last_n_closes: List[float]
    indicators: Dict[str, float]
    cache_path: str
    features_digest: str
