from typing import Protocol
import pandas as pd

class DataProvider(Protocol):
    async def candles(self, instrument: str, granularity: str, count: int = 500) -> pd.DataFrame:
        ...
