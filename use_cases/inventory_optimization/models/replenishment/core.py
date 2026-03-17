"""
Core replenishment optimisation utilities (safety-stock ROP and order quantities).

Moved here from use_cases/inventory_optimization/replenishment_optimizer.py so that
all replenishment-specific code lives under models/replenishment/.
"""

from typing import Optional

import numpy as np
import pandas as pd


def compute_demand_stats(
    orders: pd.DataFrame,
    group_cols: Optional[list[str]] = None,
    quantity_col: str = "quantity",
    date_col: str = "order_date",
    window_days: int = 90,
) -> pd.DataFrame:
    """
    Compute per-group (e.g. product_id, pharmacy_id) daily demand mean and std.
    """
    orders = orders.copy()
    orders[date_col] = pd.to_datetime(orders[date_col], errors="coerce")
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=window_days)
    orders = orders[orders[date_col] >= cutoff]
    if group_cols is None:
        group_cols = [
            c
            for c in ("product_id", "pharmacy_id", "warehouse_id")
            if c in orders.columns
        ]
    if not group_cols:
        group_cols = ["product_id"]
    orders["_date"] = orders[date_col].dt.date
    daily = (
        orders.groupby(group_cols + ["_date"])[quantity_col]
        .sum()
        .reset_index()
        .groupby(group_cols)[quantity_col]
        .agg(["mean", "std"])
        .reset_index()
    )
    daily["demand_std"] = daily["std"].fillna(0).clip(lower=0)
    daily["demand_mean"] = daily["mean"].clip(lower=0)
    return daily.rename(
        columns={"mean": "daily_demand_mean", "std": "daily_demand_std"}
    )


def safety_stock_reorder_point(
    demand_mean: float,
    demand_std: float,
    lead_time_days: float,
    service_level: float = 0.95,
) -> float:
    """
    ROP = (avg_daily_demand * lead_time) + (z * demand_std * sqrt(lead_time)).
    """
    from scipy import stats

    z = float(stats.norm.ppf(service_level))
    rop = (demand_mean * lead_time_days) + (
        z * (demand_std or 0) * np.sqrt(max(lead_time_days, 0.1))
    )
    return max(0, rop)


def compute_replenishment_recommendations(
    inventory: pd.DataFrame,
    orders: pd.DataFrame,
    lead_time_days: float = 7.0,
    service_level: float = 0.95,
    min_order_qty: Optional[float] = None,
    warehouse_col: str = "pharmacy_id",
) -> pd.DataFrame:
    """
    For each product x warehouse, compute current stock, ROP, and recommended order qty.
    """
    inv = inventory.copy()
    if warehouse_col not in inv.columns and "pharmacy_id" in inv.columns:
        inv["warehouse_id"] = inv["pharmacy_id"].astype(str)
    else:
        inv["warehouse_id"] = inv[warehouse_col].astype(str)

    orders = orders.copy()
    if "warehouse_id" not in orders.columns and "customer_id" in orders.columns:
        orders["warehouse_id"] = orders["customer_id"].astype(str)
    elif "warehouse_id" not in orders.columns and "pharmacy_id" in orders.columns:
        orders["warehouse_id"] = orders["pharmacy_id"].astype(str)

    group_cols = ["product_id", "warehouse_id"]
    demand = compute_demand_stats(
        orders,
        group_cols=group_cols,
        quantity_col="quantity" if "quantity" in orders.columns else "total_amount",
    )

    inv = inv.merge(
        demand,
        on=group_cols,
        how="left",
    )
    inv["daily_demand_mean"] = inv.get("daily_demand_mean", 0).fillna(0)
    inv["demand_std"] = inv.get("demand_std", 0).fillna(0)
    inv["lead_time_days"] = lead_time_days

    rops = []
    for _, row in inv.iterrows():
        rop = safety_stock_reorder_point(
            row["daily_demand_mean"],
            row["demand_std"],
            lead_time_days,
            service_level,
        )
        rops.append(rop)
    inv["reorder_point"] = rops

    current = pd.to_numeric(inv.get("current_stock", 0), errors="coerce").fillna(0)
    inv["below_rop"] = current < inv["reorder_point"]
    # Recommended order qty: enough to reach ROP + one lead-time of demand
    inv["reorder_qty"] = (
        (inv["reorder_point"] - current).clip(lower=0)
        + (inv["daily_demand_mean"] * lead_time_days)
    ).clip(lower=0)
    if min_order_qty is not None:
        inv.loc[inv["reorder_qty"] > 0, "reorder_qty"] = inv.loc[
            inv["reorder_qty"] > 0, "reorder_qty"
        ].clip(lower=min_order_qty)

    inv["priority"] = (inv["below_rop"].astype(int) * 2) + (
        inv["reorder_qty"] > 0
    ).astype(int)
    return inv

