"""
Local smoke test for inventory optimisation.

Goal:
- Generate/load local medallion data (handled by Makefile deps)
- Train + log MLflow model for write-off risk
- Apply by loading the MLflow model (ensuring `runs:/.../model` works)
- Run demand forecasting + replenishment apply (metrics/logs + in-memory scoring)
"""

import os

from loguru import logger

from use_cases.inventory_optimization.models.demand_forecasting.train import (
    main as demand_forecasting_train,
)
from use_cases.inventory_optimization.models.replenishment.predict import (
    main as replenishment_predict,
)
from use_cases.inventory_optimization.models.writeoff_risk.predict import (
    main as writeoff_predict,
)
from use_cases.inventory_optimization.models.writeoff_risk.train import (
    main as writeoff_train,
)


def main() -> dict:
    writeoff_res = writeoff_train()
    if not writeoff_res.get("writeoff_risk_trained"):
        raise RuntimeError(
            f"writeoff_train did not produce a model: {writeoff_res}"
        )

    model_uri = writeoff_res["model_uri"]
    os.environ["WRITEOFF_RISK_MODEL_URI"] = model_uri

    df_scores = writeoff_predict(model_uri=model_uri)
    logger.info("Inventory smoke: writeoff_score_rows={}", len(df_scores))

    # Demand forecasting and replenishment are run for completeness.
    demand_forecasting_train()
    replenishment_predict()

    return {
        "writeoff_risk": {"model_uri": model_uri, "rows": len(df_scores)},
    }


if __name__ == "__main__":
    result = main()
    logger.info("inventory smoke done: {}", result)

