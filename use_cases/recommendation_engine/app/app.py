import json
import os
import time
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st

from utils.env_utils import is_running_on_databricks


def _call_reco_endpoint(
    endpoint_url: str, customer_id: str, cart_product_ids: List[str] | None = None
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"customer_id": customer_id, "context": {}}
    if cart_product_ids:
        payload["context"]["cart"] = cart_product_ids
    try:
        start = time.time()
        resp = requests.post(endpoint_url, json=payload, timeout=10)
        duration_s = time.time() - start
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error calling recommendation endpoint: {exc}")
        return {"ok": False, "error": str(exc), "raw": None}

    # Return full JSON to allow exact comparison between endpoints.
    return {
        "ok": True,
        "status_code": resp.status_code,
        "duration_s": duration_s,
        "payload": payload,
        "raw": data,
    }


def _pretty_json(data: Any) -> str:
    try:
        return json.dumps(data, indent=2, sort_keys=False, default=str)
    except TypeError:
        return str(data)


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
    default_endpoint_url = os.environ.get("RECO_ENDPOINT_URL", "").strip()

    default_item_similarity_url = (
        os.environ.get("RECO_ENDPOINT_URL_ITEM_SIMILARITY", "").strip()
        or default_endpoint_url
    )
    default_als_url = (
        os.environ.get("RECO_ENDPOINT_URL_ALS", "").strip() or default_endpoint_url
    )
    default_lightfm_url = (
        os.environ.get("RECO_ENDPOINT_URL_LIGHTFM", "").strip() or default_endpoint_url
    )

    with st.sidebar:
        st.markdown("**Environment**")
        st.write("Running on Databricks:" if on_db else "Running locally")
        st.write(
            f"Default endpoint configured: {'yes' if default_endpoint_url else 'no'}"
        )
        st.markdown("---")

        st.markdown("**Compare endpoints**")
        endpoint_choice = st.selectbox(
            "Endpoint",
            options=[
                "Item Similarity",
                "ALS",
                "LightFM",
                "Compare All",
            ],
            index=0,
        )

        # Allow overriding URLs in the UI so users can test without redeploying.
        with st.expander("Endpoint URLs (invocations)", expanded=False):
            item_similarity_url = st.text_input(
                "Item Similarity endpoint URL",
                value=default_item_similarity_url,
            )
            als_url = st.text_input("ALS endpoint URL", value=default_als_url)
            lightfm_url = st.text_input(
                "LightFM endpoint URL", value=default_lightfm_url
            )

        st.markdown("**Input payload**")
        if "customer_id" not in st.session_state:
            st.session_state["customer_id"] = "C001"
        if "cart_raw" not in st.session_state:
            st.session_state["cart_raw"] = "P001,P002"

        customer_id = st.text_input(
            "Customer ID",
            value=st.session_state["customer_id"],
            key="customer_id",
        )
        cart_raw = st.text_input(
            "Cart product IDs (comma separated)",
            value=st.session_state["cart_raw"],
            key="cart_raw",
        )
        cart_ids = [c.strip() for c in cart_raw.split(",") if c.strip()]
        top_k = st.slider("Top K recommendations", min_value=5, max_value=50, value=10)

        st.markdown("**Example inputs**")
        if st.button("Example: C001 / P001,P002"):
            st.session_state["customer_id"] = "C001"
            st.session_state["cart_raw"] = "P001,P002"
        if st.button("Example: C010 / P005,P006,P007"):
            st.session_state["customer_id"] = "C010"
            st.session_state["cart_raw"] = "P005,P006,P007"
        if st.button("Example: C123 / P020"):
            st.session_state["customer_id"] = "C123"
            st.session_state["cart_raw"] = "P020"

    col_live, col_batch = st.columns(2)

    with col_live:
        st.subheader("Live Recommendations (Serving Endpoint)")

        urls = {
            "Item Similarity": item_similarity_url,
            "ALS": als_url,
            "LightFM": lightfm_url,
        }

        def _has_url(url: str) -> bool:
            return isinstance(url, str) and url.strip() != ""

        if st.button("Get recommendations"):
            if endpoint_choice == "Compare All":
                for label, url in urls.items():
                    if not _has_url(url):
                        st.warning(f"Skipping {label}: missing endpoint URL.")
                        continue
                    resp = _call_reco_endpoint(url, customer_id, cart_ids)
                    with st.expander(f"{label} - full JSON output"):
                        st.code(_pretty_json(resp), language="json")

                    # Optional convenience view for list-like `raw.results`.
                    raw = resp.get("raw")
                    results = (
                        raw.get("results")
                        if isinstance(raw, dict) and "results" in raw
                        else raw
                    )
                    if isinstance(results, list):
                        df = pd.DataFrame(results).head(top_k)
                        st.dataframe(df)
                    else:
                        st.info(
                            f"{label}: response raw is not a list; see JSON output."
                        )
            else:
                url = urls[endpoint_choice]
                if not _has_url(url):
                    st.warning(
                        f"Missing endpoint URL for {endpoint_choice}. "
                        "Set it in the Endpoint URLs expander or provide RECO_ENDPOINT_URL fallback."
                    )
                else:
                    resp = _call_reco_endpoint(url, customer_id, cart_ids)
                    with st.expander(
                        f"{endpoint_choice} - full JSON output", expanded=True
                    ):
                        st.code(_pretty_json(resp), language="json")

                    raw = resp.get("raw")
                    results = (
                        raw.get("results")
                        if isinstance(raw, dict) and "results" in raw
                        else raw
                    )
                    if isinstance(results, list):
                        st.dataframe(pd.DataFrame(results).head(top_k))
                    else:
                        st.info("No list-like results found; see JSON output.")

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
