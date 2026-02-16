from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
import math
import random

ORDER_MATCH_COLS = [
    "order_id",
    "timestamp",
    "outcome",
    "side",
    "price",
    "original_size",
    "matched_qty",
    "unmatched_qty",
    "status",
    "trade_count",
    "matched_with_order_ids",
]


@dataclass
class Offer:
    order_id: int
    outcome: str  # "A" or "B"
    side: str  # "bid" or "ask"
    price: float
    size: float
    timestamp: int


def _clamp_price(p: float, eps: float = 1e-6) -> float:
    return min(max(float(p), eps), 1.0 - eps)


def _logit(p: float) -> float:
    p = _clamp_price(p)
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _sample_bounded_probability(mean: float, std: float) -> float:
    """
    Sample in (0,1) via a normal distribution in logit space.
    This reshapes the distribution instead of hard-clipping normal draws.
    """
    eps = 1e-6
    m = _clamp_price(mean, eps)
    safe_std = max(1e-8, float(std))
    mu = _logit(m)
    # Delta-method approximation to map std in probability space into logit space.
    sigma = safe_std / max(eps, m * (1.0 - m))
    z = random.gauss(mu, sigma)
    return _clamp_price(_sigmoid(z), eps)


def _sample_n_offers(x_dist: Callable[[], float]) -> int:
    return max(1, int(round(float(x_dist()))))


def _match_same_outcome(offers: List[Offer]) -> List[Dict[str, float]]:
    bids_by_outcome: Dict[str, List[Offer]] = {"A": [], "B": []}
    asks_by_outcome: Dict[str, List[Offer]] = {"A": [], "B": []}
    trades: List[Dict[str, float]] = []

    for o in offers:
        outcome = o.outcome
        if o.side == "bid":
            book = asks_by_outcome[outcome]
            # Price-time priority on asks: best ask first, then earliest.
            book.sort(key=lambda v: (v.price, v.timestamp))
            remaining = o.size
            i = 0
            while i < len(book) and remaining > 0:
                ask = book[i]
                if o.price >= ask.price:
                    qty = min(remaining, ask.size)
                    trade_price = ask.price
                    trades.append(
                        {
                            "outcome": outcome,
                            "qty": qty,
                            "price": trade_price,
                            "bid_price": o.price,
                            "ask_price": ask.price,
                            "captured_spread": max(0.0, o.price - ask.price),
                            "bid_order_id": o.order_id,
                            "ask_order_id": ask.order_id,
                            "timestamp": o.timestamp,
                        }
                    )
                    remaining -= qty
                    ask.size -= qty
                    if ask.size <= 0:
                        book.pop(i)
                    else:
                        i += 1
                else:
                    break
            if remaining > 0:
                bids_by_outcome[outcome].append(
                    Offer(
                        order_id=o.order_id,
                        outcome=o.outcome,
                        side=o.side,
                        price=o.price,
                        size=remaining,
                        timestamp=o.timestamp,
                    )
                )
        else:
            book = bids_by_outcome[outcome]
            # Price-time priority on bids: best bid first, then earliest.
            book.sort(key=lambda v: (-v.price, v.timestamp))
            remaining = o.size
            i = 0
            while i < len(book) and remaining > 0:
                bid = book[i]
                if bid.price >= o.price:
                    qty = min(remaining, bid.size)
                    trade_price = bid.price
                    trades.append(
                        {
                            "outcome": outcome,
                            "qty": qty,
                            "price": trade_price,
                            "bid_price": bid.price,
                            "ask_price": o.price,
                            "captured_spread": max(0.0, bid.price - o.price),
                            "bid_order_id": bid.order_id,
                            "ask_order_id": o.order_id,
                            "timestamp": o.timestamp,
                        }
                    )
                    remaining -= qty
                    bid.size -= qty
                    if bid.size <= 0:
                        book.pop(i)
                    else:
                        i += 1
                else:
                    break
            if remaining > 0:
                asks_by_outcome[outcome].append(
                    Offer(
                        order_id=o.order_id,
                        outcome=o.outcome,
                        side=o.side,
                        price=o.price,
                        size=remaining,
                        timestamp=o.timestamp,
                    )
                )

    return trades


def _build_order_match_report(
    offers: List[Offer], trades: List[Dict[str, float]]
) -> List[Dict[str, object]]:
    matched_qty_by_order: Dict[int, float] = {o.order_id: 0.0 for o in offers}
    counterparties_by_order: Dict[int, List[int]] = {o.order_id: [] for o in offers}
    trade_count_by_order: Dict[int, int] = {o.order_id: 0 for o in offers}

    for tr in trades:
        bid_id = int(tr["bid_order_id"])
        ask_id = int(tr["ask_order_id"])
        qty = float(tr["qty"])

        matched_qty_by_order[bid_id] += qty
        matched_qty_by_order[ask_id] += qty
        counterparties_by_order[bid_id].append(ask_id)
        counterparties_by_order[ask_id].append(bid_id)
        trade_count_by_order[bid_id] += 1
        trade_count_by_order[ask_id] += 1

    report: List[Dict[str, object]] = []
    for o in offers:
        matched_qty = matched_qty_by_order[o.order_id]
        unmatched_qty = max(0.0, o.size - matched_qty)
        report.append(
            {
                "order_id": o.order_id,
                "timestamp": o.timestamp,
                "outcome": o.outcome,
                "side": o.side,
                "price": o.price,
                "original_size": o.size,
                "matched_qty": matched_qty,
                "unmatched_qty": unmatched_qty,
                "status": "matched" if matched_qty > 0 else "unmatched",
                "trade_count": trade_count_by_order[o.order_id],
                "matched_with_order_ids": counterparties_by_order[o.order_id],
            }
        )
    return report


def _compute_midpoint_probabilities(order_match_report: List[Dict[str, object]]) -> Dict[str, object]:
    best_quotes = {
        "A": {"best_bid": math.nan, "best_ask": math.nan},
        "B": {"best_bid": math.nan, "best_ask": math.nan},
    }

    for outcome in ("A", "B"):
        unmatched_rows = [
            r
            for r in order_match_report
            if r["outcome"] == outcome and float(r["unmatched_qty"]) > 0
        ]
        bids = [float(r["price"]) for r in unmatched_rows if r["side"] == "bid"]
        asks = [float(r["price"]) for r in unmatched_rows if r["side"] == "ask"]
        if bids:
            best_quotes[outcome]["best_bid"] = max(bids)
        if asks:
            best_quotes[outcome]["best_ask"] = min(asks)

    raw_mid = {"A": math.nan, "B": math.nan}
    for outcome in ("A", "B"):
        bb = best_quotes[outcome]["best_bid"]
        ba = best_quotes[outcome]["best_ask"]
        if not math.isnan(bb) and not math.isnan(ba):
            raw_mid[outcome] = (bb + ba) / 2.0

    pa_raw = raw_mid["A"]
    pb_raw = raw_mid["B"]
    if math.isnan(pa_raw) and math.isnan(pb_raw):
        pa, pb = math.nan, math.nan
    elif math.isnan(pa_raw):
        pb = pb_raw
        pa = 1.0 - pb
    elif math.isnan(pb_raw):
        pa = pa_raw
        pb = 1.0 - pa
    else:
        denom = pa_raw + pb_raw
        if denom > 0:
            pa = pa_raw / denom
            pb = pb_raw / denom
        else:
            pa, pb = math.nan, math.nan

    return {
        "raw_midpoint_prices": raw_mid,
        "normalized_probabilities": {"A": pa, "B": pb},
        "best_quotes": best_quotes,
    }


def simulate_two_outcome_market(
    x_dist: Callable[[], float],
    y: float,
    *,
    bettor_std: float = 0.08,
    ask_spread_mean: float = 0.03,
    ask_spread_std: float = 0.015,
    rng_seed: Optional[int] = None,
) -> Dict[str, object]:
    """
    Simulate a two-outcome order flow and market matching.

    Parameters
    ----------
    x_dist
        Callable sampling the number of offers (e.g. lambda: random.gauss(10, 5)).
    y
        Fixed base probability for outcome A.
    bettor_std
        Std-dev for bettors' perceived probability around y.
    ask_spread_mean, ask_spread_std
        Mean/std add-on for ask prices above perceived probability.
    rng_seed
        Optional seed for reproducibility.
    """
    if rng_seed is not None:
        random.seed(rng_seed)

    y = _clamp_price(y)
    n_offers = _sample_n_offers(x_dist)
    offers: List[Offer] = []

    for t in range(n_offers):
        p_a = _sample_bounded_probability(y, bettor_std)
        p_b = _clamp_price(1.0 - p_a)
        size = 1.0
        outcome = "A" if random.random() < 0.5 else "B"
        side = "bid" if random.random() < 0.5 else "ask"
        fair = p_a if outcome == "A" else p_b
        spread = max(0.0, random.gauss(ask_spread_mean, ask_spread_std))
        if side == "bid":
            price = fair
        else:
            price = _clamp_price(fair + spread)

        offers.append(
            Offer(
                order_id=t + 1,
                outcome=outcome,
                side=side,
                price=price,
                size=size,
                timestamp=t + 1,
            )
        )

    bids_A_ranked = sorted(
        [o for o in offers if o.outcome == "A" and o.side == "bid"],
        key=lambda o: o.timestamp,
    )
    bids_B_ranked = sorted(
        [o for o in offers if o.outcome == "B" and o.side == "bid"],
        key=lambda o: o.timestamp,
    )

    trades = _match_same_outcome(offers)
    order_match_report = _build_order_match_report(offers, trades)

    by_outcome = {"A": [], "B": []}
    for tr in trades:
        by_outcome[tr["outcome"]].append(tr)

    weighted_avg = {}
    for outcome in ("A", "B"):
        ts = by_outcome[outcome]
        vol = sum(t["qty"] for t in ts)
        if vol > 0:
            weighted_avg[outcome] = sum(t["price"] * t["qty"] for t in ts) / vol
        else:
            weighted_avg[outcome] = math.nan

    midpoint_info = _compute_midpoint_probabilities(order_match_report)
    market_probs = midpoint_info["normalized_probabilities"]

    # Exchange profit from captured spread on each match: (bid - ask) * qty.
    exchange_profit_A = sum(
        tr["captured_spread"] * tr["qty"]
        for tr in trades
        if tr["outcome"] == "A"
    )
    exchange_profit_B = sum(
        tr["captured_spread"] * tr["qty"]
        for tr in trades
        if tr["outcome"] == "B"
    )
    exchange_profit = {
        "A": exchange_profit_A,
        "B": exchange_profit_B,
        "total": exchange_profit_A + exchange_profit_B,
    }

    # Return DataFrames directly (no fallback logic).
    import pandas as pd  # type: ignore

    order_match_df = pd.DataFrame(order_match_report).sort_values("order_id").reset_index(drop=True)
    order_match_df_display = order_match_df[ORDER_MATCH_COLS].sort_values("order_id").reset_index(drop=True)

    return {
        "n_offers": n_offers,
        "base_probability_y_for_A": y,
        "offers": [
            {
                "order_id": o.order_id,
                "outcome": o.outcome,
                "side": o.side,
                "price": o.price,
                "size": o.size,
                "timestamp": o.timestamp,
            }
            for o in offers
        ],
        "ranked_bids_by_arrival": {
            "A": [
                {
                    "rank": i + 1,
                    "order_id": o.order_id,
                    "price": o.price,
                    "size": o.size,
                    "timestamp": o.timestamp,
                }
                for i, o in enumerate(bids_A_ranked)
            ],
            "B": [
                {
                    "rank": i + 1,
                    "order_id": o.order_id,
                    "price": o.price,
                    "size": o.size,
                    "timestamp": o.timestamp,
                }
                for i, o in enumerate(bids_B_ranked)
            ],
        },
        "trades": trades,
        "order_match_report": order_match_report,
        "order_match_df": order_match_df,
        "order_match_df_display": order_match_df_display,
        "matched_volume": {
            "A": sum(t["qty"] for t in by_outcome["A"]),
            "B": sum(t["qty"] for t in by_outcome["B"]),
        },
        "avg_matched_price": weighted_avg,
        "midpoint_quotes": midpoint_info["best_quotes"],
        "midpoint_raw_prices": midpoint_info["raw_midpoint_prices"],
        "market_implied_probabilities": market_probs,
        "exchange_profit": exchange_profit,
    }


if __name__ == "__main__":
    # Example usage:
    result = simulate_two_outcome_market(
        x_dist=lambda: random.gauss(10, 5),
        y=0.55,
        bettor_std=0.1,
        rng_seed=7,
    )
    print(f"Offers simulated: {result['n_offers']}")
    print("Implied probabilities:", result["market_implied_probabilities"])
