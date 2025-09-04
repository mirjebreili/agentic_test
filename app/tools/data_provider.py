from typing import Protocol
from app.tools.data_models import FeatureSummary

class DataProvider(Protocol):
    async def candles(self, instrument: str, granularity: str, count: int = 500) -> FeatureSummary:
        ...
