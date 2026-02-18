from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
import math
import pandas as pd
import numpy as np

from backtest.engine.execution import ExecutionModel, CostModelCfg
from backtest.engine.risk import (
    RiskManager,
    RiskLimits,
    Portfolio,
    Order,
    OrderType,
    Side,
    Fill,
)


class Backtester:
    def __init__(
        self,
        base_df: pd.DataFrame,
        symbol: str,
        exec_model: ExecutionModel,
        cost_cfg: CostModelCfg,
        risk_mng: RiskManager,
        strategy: Any,
    ):
        self.base_df = base_df
        self.symbol = symbol
        self.exec_model = exec_model
        self.cost_cfg = cost_cfg
        self.risk_mng = risk_mng
        self.strategy = strategy

        self.portfolio = Portfolio()
        self.fills: List[Fill] = []
        self.trades: List[Dict[str, Any]] = []

    def _mid_and_spreadbps(self, row: pd.Series) -> Tuple[float, float]:
        close_val = row["close"]
        close = float(close_val)

        if close > 1e6 or close < 0:
            raise ValueError(f"Invalid close value detected: {close}")

        spread_bps = float(row.get("spread_bps", 2.0))
        return close, spread_bps

    def _mark_to_market(self, px: float):
        px = float(px)
        eq = self.portfolio.cash

        for pos in self.portfolio.positions.values():
            eq += pos.qty * px
            if abs(pos.qty) > 1e2:
                raise ValueError(f"Position qty too big: {pos.qty}")

        if eq < 0:
            eq = 0.0
            raise ValueError("Stopped due to negative equity")

        self.portfolio.equity = eq

    def _apply_fill(self, fill: Fill):
        pos = self.portfolio.ensure_pos(fill.symbol)
        signed_qty = float(fill.qty if fill.side == Side.BUY else -fill.qty)
        notional = fill.qty * fill.price

        if (pos.qty == 0) or (np.sign(pos.qty) == np.sign(signed_qty)):
            new_qty = pos.qty + signed_qty
            numerator = pos.entry_price * abs(pos.qty) + fill.price * abs(signed_qty)
            pos.entry_price = numerator / max(abs(new_qty), 1e-9)
            pos.qty = new_qty
        else:
            new_qty = pos.qty + signed_qty
            pos.qty = new_qty
            if new_qty == 0:
                pos.entry_price = 0.0

        self.portfolio.cash += (
            -notional if fill.side == Side.BUY else notional
        ) - fill.fee

        self.trades.append(
            {
                "ts": fill.ts,
                "symbol": fill.symbol,
                "side": fill.side.value,
                "qty": fill.qty,
                "price": fill.price,
                "fee": fill.fee,
                "is_maker": fill.is_maker,
            }
        )

    def run(self) -> pd.DataFrame:
        eq_curve = []
        eq_curve.append({"ts": self.base_df.index[0], "equity": self.portfolio.equity})

        for i, (ts, row) in enumerate(self.base_df.iterrows(), start=1):
            self._refresh_sr_if_needed(i, ts)

            if not (1 < row["close"] < 100000):
                break

            orders: List[Order] = self.strategy.generate_orders(row, self.portfolio)
            mid, spread_bps = self._mid_and_spreadbps(row)

            if (
                isinstance(mid, (pd.Timestamp, np.datetime64))
                or (not np.isfinite(mid))
                or (not (1e-6 < mid < 1e6))
            ):
                raise ValueError(f"mid invalid at {ts}: {mid}")

            for o in orders:
                notional = abs(o.qty) * (o.limit_price or mid)
                if not self.risk_mng.check_pretrade(
                    ts, self.portfolio, o.symbol, notional
                ):
                    continue

                fills = self.exec_model.simulate(
                    ts,
                    o.symbol,
                    o.side,
                    o.qty,
                    o.order_type,
                    mid,
                    spread_bps,
                    o.limit_price,
                )

                for fill in fills:
                    self._apply_fill(fill)

            self._mark_to_market(px=mid)
            self.risk_mng.check_intraday_dd(ts, self.portfolio.equity)
            eq_curve.append({"ts": ts, "equity": self.portfolio.equity})

        curve = pd.DataFrame(eq_curve).set_index("ts")
        self.curve = curve
        return curve

    def tca_report(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()

        t = pd.DataFrame(self.trades)
        t["notional"] = t["qty"] * t["price"]
        t["fee_bps"] = (t["fee"] / t["notional"]).replace(
            [np.inf, -np.inf], np.nan
        ) * 10_000
        by_side = t.groupby("side").agg(
            {"notional": "sum", "fee": "sum", "fee_bps": "mean"}
        )
        by_maker = t.groupby("is_maker").agg({"notional": "sum", "fee": "sum"})
        overall = t.agg({"notional": "sum", "fee": "sum"})
        return pd.concat(
            {"overall": overall, "by_side": by_side, "by_maker": by_maker}, axis=0
        )

    def trades_report(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades).set_index("ts")


def performance_from_curve(c_eq: pd.Series) -> Dict[str, float]:
    c = c_eq.ffill()
    ret = c.pct_change().dropna()

    if ret.empty:
        return {}

    ann = 365 * 24 * 60  # 분 단위 연환산
    mean = float(ret.mean() * ann)
    vol = float(ret.std(ddof=1) * math.sqrt(ann))
    sharpe = mean / (vol + 1e-12)
    cum = float(c.iloc[-1] / c.iloc[0] - 1)
    roll_max = c.cummax()
    dd = c / roll_max - 1
    mdd = float(dd.min())
    calmar = mean / (abs(mdd) + 1e-12)

    return {
        "Cumulative": cum,
        "Sharpe": sharpe,
        "Vol_ann": vol,
        "MaxDD": mdd,
        "Calmar": calmar,
    }
