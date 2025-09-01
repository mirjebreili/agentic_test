from typing import Protocol, TypedDict

class Order(TypedDict):
    instrument: str
    side: str            # "buy" | "sell"
    units: int
    entry_type: str      # "market" | "limit"
    price: float | None
    stop_loss: float | None
    take_profit: float | None

class BrokerProvider(Protocol):
    async def place_order(self, order: Order) -> dict:
        ...
