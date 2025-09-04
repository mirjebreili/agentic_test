from __future__ import annotations
from typing import List
from langchain_core.tools import BaseTool

def get_toolset() -> List[BaseTool]:
    """
    Returns the standard set of tools for the trading agents.
    """
    from app.tools.standard import get_candles, execute_order, propose_order, attach_stops

    return [get_candles, execute_order, propose_order, attach_stops]
