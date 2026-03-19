"""
Job 2: Train write-off risk classifier; log to MLflow; register model; set @Champion.

Delegates to ``models/writeoff_risk/train.py`` so behaviour matches local training and
batch scoring (``models:/inventory_optimization-writeoff_risk@Champion``).
"""

from use_cases.inventory_optimization.models.writeoff_risk.train import main


if __name__ == "__main__":
    main()
