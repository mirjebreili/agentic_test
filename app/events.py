from dataclasses import dataclass

@dataclass
class CandleCloseEvent:
    instrument: str
    timeframe: str

@dataclass
class PriceSpikeEvent:
    instrument: str
    abs_change: float
    atr: float

@dataclass
class MacroEvent:
    high_impact: bool
    country: str
    title: str
