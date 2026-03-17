"""
Model-specific feature construction for recommendation engine.
Read from gold/silver (training_base, products, orders); used in training and serving.
"""

import numpy as np
import pandas as pd


def product_feature_columns() -> list[str]:
    """Column names used for item-similarity and content features."""
    return [
        "category",
        "therapeutic_category",
        "price_tier",
        "unit_price",
        "margin_percentage",
        "is_prescription",
        "regulatory_class",
    ]


def build_product_feature_matrix(
    products: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Build numeric feature matrix for products (item similarity / content features).
    Returns (feature_df with product_id index, label encodings for categoricals).
    """
    prods = products.copy()
    encodings = {}
    cat_cols = ["category", "therapeutic_category", "price_tier", "regulatory_class"]
    for col in cat_cols:
        if col not in prods.columns:
            continue
        prods[col] = prods[col].fillna("").astype(str)
        uniq = prods[col].unique()
        encodings[col] = {v: i for i, v in enumerate(uniq)}
        prods[f"{col}_enc"] = prods[col].map(encodings[col])
    feature_cols = [
        c
        for c in prods.columns
        if c.endswith("_enc")
        or c in ("unit_price", "margin_percentage", "is_prescription")
    ]
    for c in ["unit_price", "margin_percentage"]:
        if c in prods.columns:
            prods[c] = pd.to_numeric(prods[c], errors="coerce").fillna(0)
    if "is_prescription" in prods.columns:
        prods["is_prescription"] = prods["is_prescription"].astype(int)
    use = [c for c in feature_cols if c in prods.columns]
    if not use:
        use = [
            c
            for c in prods.select_dtypes(include=[np.number]).columns
            if c != "product_id"
        ][:10]
    out = prods.set_index("product_id")[use].fillna(0)
    return out.astype(np.float32), encodings


def build_interaction_matrix(
    interactions: pd.DataFrame,
    customer_col: str = "customer_id",
    product_col: str = "product_id",
    weight_col: str | None = None,
) -> tuple[pd.Series, pd.Series, np.ndarray]:
    """
    Build sparse user-item matrix for ALS. Returns (customer_ids, product_ids, weights).
    Weights: use weight_col if provided, else 1 for purchased and fractional for others.
    """
    df = interactions.copy()
    if weight_col and weight_col in df.columns:
        weights = df[weight_col].values
    else:
        if "action_type" in df.columns:
            w = (
                df["action_type"]
                .map({"purchased": 1.0, "added": 0.5, "viewed": 0.2, "searched": 0.1})
                .fillna(0.1)
            )
        else:
            w = pd.Series(1.0, index=df.index)
        weights = w.values.astype(np.float32)
    customers = df[customer_col].astype("category")
    products = df[product_col].astype("category")
    return (
        customers.cat.codes.values,
        products.cat.codes.values,
        weights,
        customers.cat,
        products.cat,
    )


def add_negative_samples(
    training_base: pd.DataFrame,
    products: pd.DataFrame,
    n_neg_per_pos: int = 2,
    seed: int = 42,
) -> pd.DataFrame:
    """Add negative (customer, product) pairs: products the customer did not purchase."""
    rng = np.random.default_rng(seed)
    pos = training_base[training_base["label"] == 1].copy()
    all_products = products["product_id"].unique()
    negs = []
    for _, row in pos.iterrows():
        cust = row["customer_id"]
        bought = training_base[
            (training_base["customer_id"] == cust) & (training_base["label"] == 1)
        ]["product_id"].values
        candidates = [p for p in all_products if p not in bought]
        n = min(n_neg_per_pos, len(candidates))
        if n > 0:
            chosen = rng.choice(candidates, size=n, replace=False)
            for p in chosen:
                negs.append({"customer_id": cust, "product_id": p, "label": 0})
    if negs:
        return pd.concat([training_base, pd.DataFrame(negs)], ignore_index=True)
    return training_base
