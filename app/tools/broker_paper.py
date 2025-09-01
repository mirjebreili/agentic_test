from __future__ import annotations

"""
PaperBroker — a minimal simulated broker for demo/testing.

Features:
- Accepts market/limit BUY/SELL orders with optional SL/TP.
- Fills market orders on the next bar close ± spread/slippage.
- Fills limit orders if the bar trades through the limit.
- Triggers SL/TP using the current bar's high/low.
- Marks equity each bar; records fills/closures in a JSON ledger.

This broker is intentionally simple: it assumes 1:1 price-to-PnL units
(e.g., units * price) and uses a basic pip model for spread/slippage.
It’s good for end-to-end demos without any external broker account.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional

from app.settings import settings


# --------- Data models ---------
@dataclass
class PaperPosition:
    instrument: str
    units: int             # positive = long, negative = short
    avg_price: float


@dataclass
class PaperOrder:
    id: str
    instrument: str
    side: str              # "buy" | "sell"
    units: int             # signed when stored (buy>0, sell<0)
    entry_type: str        # "market" | "limit"
    price: Optional[float] # limit price (None for market)
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: str            # "pending" | "filled" | "cancelled"
    ts: str                # ISO timestamp of order creation


@dataclass
class PaperState:
    cash: float
    equity: float
    positions: Dict[str, PaperPosition]
    open_orders: List[PaperOrder]
    history: List[dict]       # list of trade dicts (open/closed)
    last_mark: Optional[str]


# --------- Broker implementation ---------
class PaperBroker:
    """
    A simple paper-trading execution simulator persisted to JSON.
    """

    def __init__(self) -> None:
        p = getattr(settings, "paper", {}) or {}
        self.spread_pips: float = float(p.get("spread_pips", 0.8))
        self.slippage_pips: float = float(p.get("slippage_pips", 0.2))
        self.commission_per_million: float = float(p.get("commission_per_million", 0.0))
        self.lot_size: int = int(p.get("lot_size", 1000))
        self.ledger_path: Path = Path(p.get("ledger_path", "runs/paper_ledger.json"))
        initial_cash = float(p.get("initial_cash", 100_000))

        self._state = self._load(initial_cash)

    # ----- persistence -----
    def _load(self, initial_cash: float) -> PaperState:
        if self.ledger_path.exists():
            data = json.loads(self.ledger_path.read_text())
            return PaperState(
                cash=float(data.get("cash", initial_cash)),
                equity=float(data.get("equity", data.get("cash", initial_cash))),
                positions={k: PaperPosition(**v) for k, v in data.get("positions", {}).items()},
                open_orders=[PaperOrder(**o) for o in data.get("open_orders", [])],
                history=list(data.get("history", [])),
                last_mark=data.get("last_mark"),
            )
        return PaperState(
            cash=initial_cash,
            equity=initial_cash,
            positions={},
            open_orders=[],
            history=[],
            last_mark=None,
        )

    def _save(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(asdict(self._state), indent=2))

    # ----- utilities -----
    @staticmethod
    def _pip_size(instrument: str) -> float:
        """
        Very rough pip size guess: 0.01 for JPY crosses, 0.0001 otherwise.
        """
        return 0.01 if instrument.endswith("JPY") else 0.0001

    # ----- public API -----
    def place_order(self, order: dict) -> dict:
        """
        Accept an order and store it as pending. Fills occur on next on_bar().
        Expected order keys:
        {instrument, side: buy|sell, units:int, entry_type: market|limit,
         price: float|None, stop_loss: float|None, take_profit: float|None}
        """
        side = str(order["side"]).lower()
        if side not in {"buy", "sell"}:
            return {"status": "error", "reason": "invalid_side"}

        entry_type = str(order["entry_type"]).lower()
        if entry_type not in {"market", "limit"}:
            return {"status": "error", "reason": "invalid_entry_type"}

        # Signed units by side
        units = abs(int(order["units"])) * (1 if side == "buy" else -1)
        oid = f"PAPER-{len(self._state.history) + len(self._state.open_orders) + 1}"

        po = PaperOrder(
            id=oid,
            instrument=str(order["instrument"]),
            side=side,
            units=units,
            entry_type=entry_type,
            price=float(order["price"]) if entry_type == "limit" and order.get("price") is not None else None,
            stop_loss=float(order["stop_loss"]) if order.get("stop_loss") is not None else None,
            take_profit=float(order["take_profit"]) if order.get("take_profit") is not None else None,
            status="pending",
            ts=datetime.now(UTC).isoformat(),
        )
        self._state.open_orders.append(po)
        self._save()
        return {"status": "accepted", "order_id": oid}

    def on_bar(self, instrument: str, o: float, h: float, l: float, c: float) -> None:
        """
        Advance the simulation one bar and attempt fills/triggers for the given instrument
        using this bar's OHLC. Also marks-to-market equity.
        """
        pip = self._pip_size(instrument)
        ask_close = c + self.spread_pips * pip / 2
        bid_close = c - self.spread_pips * pip / 2

        # --- Fill pending orders ---
        remaining: List[PaperOrder] = []
        for od in self._state.open_orders:
            if od.instrument != instrument:
                remaining.append(od)
                continue

            if od.entry_type == "market":
                # Fill at close +/- half-spread + directional slippage
                fill_px = ask_close if od.units > 0 else bid_close
                fill_px += (self.slippage_pips * pip) * (1 if od.units > 0 else -1)
                self._fill(od, float(fill_px))
            else:
                # LIMIT: buy fills if low <= limit; sell fills if high >= limit
                limit = od.price
                if limit is None:
                    remaining.append(od)
                    continue
                if od.units > 0 and l <= limit:
                    self._fill(od, float(limit))
                elif od.units < 0 and h >= limit:
                    self._fill(od, float(limit))
                else:
                    remaining.append(od)

        self._state.open_orders = remaining

        # --- Mark-to-market current positions (simple 1:1 price * units PnL model) ---
        mtm_equity = self._state.cash
        for sym, pos in self._state.positions.items():
            # mark positions at the current instrument's close if matching, else leave as-is
            # (for a multi-symbol book, you'd want separate per-symbol prices)
            if sym == instrument:
                mtm_equity += pos.units * c
            else:
                mtm_equity += pos.units * c  # simplistic: use same close for all

        # --- Trigger SL/TP on this bar ---
        to_close: List[tuple[dict, float, str]] = []
        for hist in self._state.history:
            if hist.get("status") != "open" or hist["instrument"] != instrument:
                continue
            sl = hist.get("stop_loss")
            tp = hist.get("take_profit")
            side = hist["side"]
            # For long: SL hits if low <= SL; TP hits if high >= TP
            # For short: SL hits if high >= SL; TP hits if low <= TP
            if side == "buy":
                if sl is not None and l <= sl:
                    to_close.append((hist, float(sl), "stop_loss"))
                elif tp is not None and h >= tp:
                    to_close.append((hist, float(tp), "take_profit"))
            else:
                if sl is not None and h >= sl:
                    to_close.append((hist, float(sl), "stop_loss"))
                elif tp is not None and l <= tp:
                    to_close.append((hist, float(tp), "take_profit"))

        for hist, px, reason in to_close:
            self._close_hist(hist, px, reason)

        self._state.equity = float(mtm_equity)
        self._state.last_mark = datetime.now(UTC).isoformat()
        self._save()

    # ----- internals -----
    def _fill(self, od: PaperOrder, px: float) -> None:
        """
        Book a new/added position at price px and record the trade as 'open' in history.
        """
        notional = abs(od.units) * px
        commission = self.commission_per_million * (notional / 1_000_000.0)
        self._state.cash -= commission

        pos = self._state.positions.get(od.instrument)
        if pos is None:
            self._state.positions[od.instrument] = PaperPosition(od.instrument, od.units, px)
        else:
            new_units = pos.units + od.units
            if new_units == 0:
                # flat after netting
                self._state.positions.pop(od.instrument, None)
            else:
                pos.avg_price = (pos.avg_price * pos.units + px * od.units) / new_units
                pos.units = new_units
                self._state.positions[od.instrument] = pos

        self._state.history.append(
            {
                "status": "open",
                "instrument": od.instrument,
                "side": od.side,                # "buy"|"sell"
                "units": od.units,              # signed
                "open_price": px,
                "stop_loss": od.stop_loss,
                "take_profit": od.take_profit,
                "ts_open": od.ts,
            }
        )
        od.status = "filled"

    def _close_hist(self, hist: dict, px: float, reason: str) -> None:
        """
        Close an open trade in history at price px and realize PnL into cash.
        """
        pnl = hist["units"] * (px - hist["open_price"])
        self._state.cash += pnl

        # This logic assumes the entire position is closed by SL/TP, which is a simplification.
        instrument = hist["instrument"]
        if instrument in self._state.positions:
            del self._state.positions[instrument]

        hist.update(
            {
                "status": "closed",
                "close_price": px,
                "ts_close": datetime.now(UTC).isoformat(),
                "pnl": float(pnl),
                "close_reason": reason,
            }
        )

    # ----- helpers for external inspection -----
    def snapshot(self) -> dict:
        """Return a shallow snapshot of the ledger/state (for UI/tests)."""
        return asdict(self._state)

    def reset(self) -> None:
        """Hard reset the ledger (useful for tests)."""
        if self.ledger_path.exists():
            self.ledger_path.unlink()
        p = getattr(settings, "paper", {}) or {}
        initial_cash = float(p.get("initial_cash", 100_000))
        self._state = self._load(initial_cash)
        self._save()
