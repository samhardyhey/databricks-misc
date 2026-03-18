import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from databricks.sdk import WorkspaceClient
from loguru import logger

from utils.env_utils import is_running_on_databricks


@dataclass(frozen=True)
class DomainSpec:
    domain_key: str
    genie_space_env_var: str
    dashboard_url_env_var: str
    capabilities: List[str]


DOMAIN_SPECS: List[DomainSpec] = [
    DomainSpec(
        domain_key="healthcare_insights",
        genie_space_env_var="GENIE_HEALTHCARE_SPACE_ID",
        dashboard_url_env_var="HEALTHCARE_DASHBOARD_URL",
        capabilities=[
            "Ranging & consolidation KPIs",
            "Warehouse / handling cost impacts (if configured in the Knowledge Store)",
            "Allowed tables/columns restricted to healthcare medallion outputs",
        ],
    ),
    DomainSpec(
        domain_key="animal_care_insights",
        genie_space_env_var="GENIE_ANIMAL_CARE_SPACE_ID",
        dashboard_url_env_var="ANIMAL_CARE_DASHBOARD_URL",
        capabilities=[
            "Competitor product and price history analytics",
            "Market intelligence trends (as configured in the Knowledge Store)",
            "Allowed tables/columns restricted to animal care medallion outputs",
        ],
    ),
    DomainSpec(
        domain_key="twc_franchise_insights",
        genie_space_env_var="GENIE_TWC_SPACE_ID",
        dashboard_url_env_var="TWC_DASHBOARD_URL",
        capabilities=[
            "Store clusters and similarity groups",
            "Promotion impact and store-level recommendations",
            "Allowed tables/columns restricted to franchise medallion outputs",
        ],
    ),
]


def _get_domain_spec(domain_key: str) -> DomainSpec:
    for spec in DOMAIN_SPECS:
        if spec.domain_key == domain_key:
            return spec
    raise KeyError(f"Unknown domain: {domain_key}")


def _get_env_trim(name: str) -> str:
    return os.environ.get(name, "").strip()


def _build_active_domain_prompt_prefix(domain_key: str) -> str:
    # Domain prompt guardrail: makes the active domain explicit to the Genie space.
    return (
        "Active domain: "
        + domain_key
        + ". Answer using only the domain-specific KPI definitions and tables for this space."
    )


def _safe_sleep(seconds: float) -> None:
    try:
        time.sleep(seconds)
    except Exception:  # noqa: BLE001
        # best-effort; Streamlit should still continue
        pass


def _looks_like_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many" in msg


def _extract_statement_to_df(w: WorkspaceClient, statement_id: str) -> pd.DataFrame:
    result = w.statement_execution.get_statement(statement_id)
    columns = [i.name for i in result.manifest.schema.columns]
    return pd.DataFrame(result.result.data_array, columns=columns)


def _get_dashboard_url(domain_spec: DomainSpec) -> str:
    return _get_env_trim(domain_spec.dashboard_url_env_var)


def _init_session_state() -> None:
    if "active_domain" not in st.session_state:
        st.session_state.active_domain = "healthcare_insights"
    if "conversation_ids" not in st.session_state:
        st.session_state.conversation_ids: Dict[str, str] = {}
    if "messages" not in st.session_state:
        # UI history only; Genie conversation state is stored separately per domain.
        st.session_state.messages: List[Dict[str, str]] = []


def _start_or_continue_conversation(
    w: WorkspaceClient,
    genie_space_id: str,
    domain_key: str,
    prompt: str,
) -> Any:
    """
    Starts a new Genie conversation (if needed) or continues an existing one.
    Returns the Genie conversation response object and updates conversation_id in session state.
    """
    max_retries = 3
    base_backoff_s = 2.0

    conversation_id = st.session_state.conversation_ids.get(domain_key)

    # Genie APIs are synchronous; keep retries bounded for UX.
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            if conversation_id:
                response = w.genie.create_message_and_wait(
                    genie_space_id, conversation_id, prompt
                )
            else:
                response = w.genie.start_conversation_and_wait(genie_space_id, prompt)
                # response objects are expected to include the conversation id
                # (SDK attribute differs by version; fall back to session assignment).
                st.session_state.conversation_ids[domain_key] = getattr(
                    response, "conversation_id", conversation_id
                ) or getattr(st.session_state, "conversation_id", conversation_id)
                conversation_id = st.session_state.conversation_ids[domain_key]

            # Ensure session has a conversation_id for subsequent prompts in this domain.
            if not st.session_state.conversation_ids.get(domain_key):
                st.session_state.conversation_ids[domain_key] = getattr(
                    response, "conversation_id", conversation_id
                )
            return response
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Genie conversation call failed: {}", exc)
            if not _looks_like_rate_limit(exc) or attempt == max_retries - 1:
                raise
            _safe_sleep(base_backoff_s * (attempt + 1))

    # Should be unreachable due to raise logic.
    raise last_exc  # type: ignore[misc]


def _render_genie_attachments(
    w: WorkspaceClient, response: Any, domain_key: str
) -> None:
    for attachment in getattr(response, "attachments", []) or []:
        if getattr(attachment, "text", None) is not None:
            st.markdown(attachment.text.content)
        elif getattr(attachment, "query", None) is not None:
            query = attachment.query
            if getattr(query, "description", None):
                st.write(query.description)
            statement_id = attachment.query_result.statement_id  # type: ignore[attr-defined]
            with st.expander("Show generated SQL"):
                if getattr(query, "query", None):
                    st.code(query.query, language="sql")
            with st.spinner("Running SQL to fetch results..."):
                try:
                    df = _extract_statement_to_df(w, statement_id)
                except Exception as exc:  # noqa: BLE001
                    st.error(
                        "Failed to fetch statement results. "
                        "This can happen if the statement link expired. "
                        "Try asking again."
                    )
                    logger.warning("Statement fetch failed: {}", exc)
                    continue
                st.dataframe(df)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{domain_key}_genie_results.csv",
                    mime="text/csv",
                    key=f"dl_{domain_key}_{statement_id}",
                )

    message_id = getattr(response, "message_id", None)
    if message_id:
        rating = st.feedback("thumbs", key=f"feedback_{message_id}")
        if rating:
            # Cookbook mapping is 1 -> POSITIVE, 0 -> NEGATIVE
            # We guard in case SDK enum differs.
            try:
                from databricks.sdk.service.dashboards import (
                    GenieFeedbackRating,
                )  # type: ignore

                mapping = {
                    1: GenieFeedbackRating.POSITIVE,
                    0: GenieFeedbackRating.NEGATIVE,
                }
                genie_space_id = _get_env_trim(
                    _get_domain_spec(domain_key).genie_space_env_var
                )
                w.genie.send_message_feedback(
                    genie_space_id,
                    st.session_state.conversation_ids.get(domain_key),
                    message_id,
                    mapping.get(rating, GenieFeedbackRating.POSITIVE),
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Feedback submission skipped: {}", exc)


def main() -> None:
    st.set_page_config(
        page_title="AI Powered Insights (Genie + Dashboards)", layout="wide"
    )
    st.title("AI Powered Insights")

    _init_session_state()

    domain_keys = [s.domain_key for s in DOMAIN_SPECS]
    active_domain = st.selectbox(
        "Domain",
        options=domain_keys,
        index=(
            domain_keys.index(st.session_state.active_domain)
            if st.session_state.active_domain in domain_keys
            else 0
        ),
    )
    st.session_state.active_domain = active_domain
    domain_spec = _get_domain_spec(active_domain)

    genie_space_id = _get_env_trim(domain_spec.genie_space_env_var)
    if not genie_space_id:
        st.error(
            f"Missing Genie Space ID env var `{domain_spec.genie_space_env_var}`. "
            "Configure it to enable chat for this domain."
        )

    with st.sidebar:
        st.markdown("**Capabilities (active domain)**")
        st.info(active_domain)
        for cap in domain_spec.capabilities:
            st.write(f"- {cap}")

        st.markdown("---")
        if not is_running_on_databricks():
            st.markdown("**Local mode**")
            st.write(
                "Set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` env vars for the Databricks SDK."
            )

        dashboard_url = _get_dashboard_url(domain_spec)
        if dashboard_url:
            st.markdown("---")
            st.markdown(f"**Domain dashboard:** [Open]({dashboard_url})")

    user_prompt = st.chat_input("Ask a question about your data...")
    if not user_prompt:
        return

    # Persist UI history and guardrail the prompt with the active domain.
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.chat_message("user").markdown(user_prompt)

    guarded_prompt = (
        _build_active_domain_prompt_prefix(active_domain) + "\n\n" + user_prompt
    )

    on_db = is_running_on_databricks()
    if not on_db and not (
        _get_env_trim("DATABRICKS_HOST") and _get_env_trim("DATABRICKS_TOKEN")
    ):
        st.error("Missing `DATABRICKS_HOST` / `DATABRICKS_TOKEN` for local execution.")
        return

    w = WorkspaceClient()

    with st.status(
        "Starting Genie conversation and generating answer...", expanded=True
    ) as status:
        try:
            with st.spinner("Contacting Genie (may take 10–30 seconds)..."):
                response = _start_or_continue_conversation(
                    w=w,
                    genie_space_id=genie_space_id,
                    domain_key=active_domain,
                    prompt=guarded_prompt,
                )
            status.update(label="Rendering response", state="complete")
        except Exception as exc:  # noqa: BLE001
            if _looks_like_rate_limit(exc):
                st.error("Genie is busy (429 rate limit). Please retry in a moment.")
                return
            logger.exception("Genie call failed")
            st.error(f"Genie call failed: {exc}")
            return

    st.chat_message("assistant")
    _render_genie_attachments(w=w, response=response, domain_key=active_domain)

    # Domain dashboard deep-link (optional).
    dashboard_url = _get_dashboard_url(domain_spec)
    if dashboard_url:
        if st.button("View full dashboard", key=f"dash_{active_domain}"):
            st.markdown(f"[Open dashboard]({dashboard_url})", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
