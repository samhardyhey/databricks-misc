import os
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st

from use_cases.env_utils import is_running_on_databricks


def _call_reco_endpoint(
    endpoint_url: str, customer_id: str, cart_product_ids: List[str] | None = None
) -> List[Dict[str, Any]]:
    payload: Dict[str, Any] = {"customer_id": customer_id, "context": {}}
    if cart_product_ids:
        payload["context"]["cart"] = cart_product_ids
    try:
        resp = requests.post(endpoint_url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error calling recommendation endpoint: {exc}")
        return []
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def _load_sample_candidates(local_path: str | None = None) -> pd.DataFrame | None:
    """
    Fallback for local development when no serving endpoint is configured.
    Tries to load a pre-computed candidates CSV from data/local.
    """
    path = local_path or os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "data",
        "local",
        "gold_reco_candidates.csv",
    )
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return None


def main() -> None:
    st.set_page_config(page_title="Recommendation Engine Demo", layout="wide")
    st.title("Recommendation Engine Demo")

    on_db = is_running_on_databricks()
    endpoint_url = os.environ.get("RECO_ENDPOINT_URL", "").strip()

    with st.sidebar:
        st.markdown("**Environment**")
        st.write("Running on Databricks:" if on_db else "Running locally")
        st.write(f"Endpoint configured: {'yes' if endpoint_url else 'no'}")
        st.markdown("---")
        customer_id = st.text_input("Customer ID", value="C001")
        cart_raw = st.text_input(
            "Cart product IDs (comma separated)", value="P001,P002"
        )
        cart_ids = [c.strip() for c in cart_raw.split(",") if c.strip()]
        top_k = st.slider("Top K recommendations", min_value=5, max_value=50, value=10)

    col_live, col_batch = st.columns(2)

    with col_live:
        st.subheader("Live Recommendations (Serving Endpoint)")
        if endpoint_url:
            if st.button("Get live recommendations"):
                recs = _call_reco_endpoint(endpoint_url, customer_id, cart_ids)
                if not recs:
                    st.info("No recommendations returned.")
                else:
                    df = pd.DataFrame(recs).head(top_k)
                    st.dataframe(df)
        else:
            st.info(
                "No `RECO_ENDPOINT_URL` configured. "
                "Set this env var to point at the Databricks serving endpoint."
            )

    with col_batch:
        st.subheader("Batch Recommendations (gold_reco_candidates)")
        candidates = _load_sample_candidates()
        if candidates is None:
            st.info(
                "No local `gold_reco_candidates.csv` found. "
                "Generate batch candidates on Databricks and export locally to enable this view."
            )
        else:
            subset = candidates[candidates["customer_id"] == customer_id].head(top_k)
            if subset.empty:
                st.info(f"No batch candidates found for customer {customer_id}.")
            else:
                st.dataframe(subset)


if __name__ == "__main__":
    main()
