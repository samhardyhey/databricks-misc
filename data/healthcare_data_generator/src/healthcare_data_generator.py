"""
Healthcare Data Generator for pharmaceutical distribution scenarios.

This module generates synthetic datasets for healthcare/pharmaceutical distribution
including pharmacies, hospitals, products, orders, and supply chain data.
"""

import random
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
from faker import Faker
from faker.providers import BaseProvider
from loguru import logger

# Configuration constants
DEFAULT_SIZES = {
    "pharmacies": 100,
    "hospitals": 50,
    "suppliers": 80,
    "products": 1000,
    "orders": 5000,
    "inventory": 10000,
    "events": 2000,
    "product_interactions": 15000,
    "substitution_events_ratio": 0.1,
    "purchase_orders": 3000,
    "writeoff_events": 500,
    "competitor_products": 200,
    "store_sales_days": 90,
    "promotions": 200,
}

DISCOUNT_THRESHOLDS = {
    "high_volume": {"min_quantity": 50, "discount_range": (0.05, 0.15)},
    "medium_volume": {"min_quantity": 20, "discount_range": (0.02, 0.08)},
    "low_volume": {"min_quantity": 1, "discount_range": (0.0, 0.0)},
}


class HealthcareProvider(BaseProvider):
    """Custom Faker provider for healthcare-specific data."""

    # Australian pharmaceutical categories
    PHARMA_CATEGORIES = [
        "Prescription Medicines",
        "Over-the-Counter",
        "Vaccines",
        "Medical Devices",
        "Surgical Supplies",
        "Diagnostic Equipment",
        "Therapeutic Devices",
        "Dental Supplies",
        "Veterinary Medicines",
        "Complementary Medicines",
    ]

    # Australian states/territories
    AU_STATES = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]

    # Common Australian pharmacy chains
    PHARMACY_CHAINS = [
        "TerryWhite Chemmart",
        "Priceline Pharmacy",
        "Amcal",
        "Pharmacy 4 Less",
        "Chemist Warehouse",
        "Guardian Pharmacy",
        "Discount Drug Store",
        "Independent Pharmacy",
        "HealthSave Pharmacy",
        "Pharmacy Direct",
    ]

    # Hospital types
    HOSPITAL_TYPES = [
        "Public Hospital",
        "Private Hospital",
        "Teaching Hospital",
        "Regional Hospital",
        "Specialist Hospital",
        "Day Surgery",
        "Community Health Centre",
    ]

    # Product storage requirements
    STORAGE_TYPES = [
        "Room Temperature",
        "Refrigerated (2-8°C)",
        "Frozen (-20°C)",
        "Controlled Room Temperature",
        "Cold Chain",
        "Ambient",
        "Special Storage",
    ]

    def pharma_category(self) -> str:
        """Generate a pharmaceutical category."""
        return self.random_element(self.PHARMA_CATEGORIES)

    def au_state(self) -> str:
        """Generate an Australian state/territory."""
        return self.random_element(self.AU_STATES)

    def pharmacy_chain(self) -> str:
        """Generate a pharmacy chain name."""
        return self.random_element(self.PHARMACY_CHAINS)

    def hospital_type(self) -> str:
        """Generate a hospital type."""
        return self.random_element(self.HOSPITAL_TYPES)

    def storage_type(self) -> str:
        """Generate a storage requirement."""
        return self.random_element(self.STORAGE_TYPES)

    def australian_phone(self) -> str:
        """Generate an Australian phone number."""
        area_code = self.random_element(["02", "03", "07", "08"])
        if area_code in ["02", "03", "07", "08"]:
            number = self.random_int(min=10000000, max=99999999)
        else:
            number = self.random_int(min=1000000, max=9999999)
        return f"{area_code} {number:08d}"

    def australian_postcode(self) -> str:
        """Generate an Australian postcode."""
        return str(self.random_int(min=1000, max=9999))

    def pbs_code(self) -> str:
        """Generate a PBS (Pharmaceutical Benefits Scheme) code."""
        return f"PBS{self.random_int(min=10000, max=99999)}"

    def atc_code(self) -> str:
        """Generate an ATC (Anatomical Therapeutic Chemical) code."""
        return f"{self.random_letter()}{self.random_int(min=10, max=99)}{self.random_letter()}{self.random_int(min=10, max=99)}{self.random_letter()}{self.random_int(min=10, max=99)}"


class HealthcareDataGenerator:
    """Main class for generating healthcare/pharmaceutical datasets."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize the data generator with optional seed for reproducibility."""
        if seed:
            Faker.seed(seed)
            np.random.seed(seed)
            random.seed(seed)

        self.fake = Faker("en_AU")  # Australian locale
        self.fake.add_provider(HealthcareProvider)

        logger.info(f"HealthcareDataGenerator initialized with seed: {seed}")

    def generate_pharmacies(self, n_pharmacies: int = 100) -> pd.DataFrame:
        """Generate pharmacy dataset."""
        logger.info(f"Generating {n_pharmacies} pharmacies...")

        data = []
        for _ in range(n_pharmacies):
            pharmacy_id = f"PHARM_{self.fake.random_int(min=10000, max=99999)}"
            is_chain = self.fake.boolean(chance_of_getting_true=70)

            data.append(
                {
                    "pharmacy_id": pharmacy_id,
                    "name": (
                        self.fake.pharmacy_chain()
                        if is_chain
                        else f"{self.fake.last_name()} Pharmacy"
                    ),
                    "is_chain": is_chain,
                    "address": self.fake.street_address(),
                    "suburb": self.fake.city(),
                    "state": self.fake.au_state(),
                    "postcode": self.fake.australian_postcode(),
                    "phone": self.fake.australian_phone(),
                    "email": self.fake.email(),
                    "license_number": f"PH{self.fake.random_int(min=100000, max=999999)}",
                    "established_date": self.fake.date_between(
                        start_date="-50y", end_date="today"
                    ),
                    "pharmacist_in_charge": self.fake.name(),
                    "trading_hours": f"{self.fake.random_int(min=6, max=8)}:00 AM - {self.fake.random_int(min=8, max=10)}:00 PM",
                    "has_consultation_room": self.fake.boolean(
                        chance_of_getting_true=60
                    ),
                    "has_vaccination_service": self.fake.boolean(
                        chance_of_getting_true=80
                    ),
                    "monthly_revenue": self.fake.random_int(min=50000, max=500000),
                    "customer_count": self.fake.random_int(min=500, max=5000),
                }
            )

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} pharmacies")
        return df

    def generate_hospitals(self, n_hospitals: int = 50) -> pd.DataFrame:
        """Generate hospital dataset."""
        logger.info(f"Generating {n_hospitals} hospitals...")

        data = []
        for _ in range(n_hospitals):
            hospital_id = f"HOSP_{self.fake.random_int(min=1000, max=9999)}"

            data.append(
                {
                    "hospital_id": hospital_id,
                    "name": f"{self.fake.city()} {self.fake.hospital_type()}",
                    "hospital_type": self.fake.hospital_type(),
                    "address": self.fake.street_address(),
                    "suburb": self.fake.city(),
                    "state": self.fake.au_state(),
                    "postcode": self.fake.australian_postcode(),
                    "phone": self.fake.australian_phone(),
                    "email": self.fake.email(),
                    "license_number": f"HOSP{self.fake.random_int(min=10000, max=99999)}",
                    "beds": self.fake.random_int(min=20, max=1000),
                    "emergency_department": self.fake.boolean(
                        chance_of_getting_true=85
                    ),
                    "icu_beds": self.fake.random_int(min=0, max=50),
                    "specialties": ", ".join(self.fake.words(nb=3)),
                    "accreditation_date": self.fake.date_between(
                        start_date="-20y", end_date="today"
                    ),
                    "monthly_budget": self.fake.random_int(min=100000, max=10000000),
                    "procurement_contact": self.fake.name(),
                    "procurement_email": self.fake.email(),
                }
            )

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} hospitals")
        return df

    def generate_suppliers(self, n_suppliers: int = 80) -> pd.DataFrame:
        """Generate supplier dataset (foundation for products and purchase orders)."""
        logger.info(f"Generating {n_suppliers} suppliers...")
        data = []
        for _ in range(n_suppliers):
            data.append(
                {
                    "supplier_id": f"SUP_{self.fake.random_int(min=10000, max=99999)}",
                    "name": f"{self.fake.company()} Medical Supplies",
                    "region": self.fake.au_state(),
                    "lead_time_days": self.fake.random_int(min=1, max=21),
                }
            )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} suppliers")
        return df

    def generate_warehouses(self, pharmacy_df: pd.DataFrame) -> pd.DataFrame:
        """Generate warehouse dataset (1:1 with pharmacies as stock locations)."""
        logger.info("Generating warehouses from pharmacies...")
        df = pharmacy_df[["pharmacy_id", "name", "state"]].copy()
        df = df.rename(
            columns={
                "pharmacy_id": "warehouse_id",
                "name": "name",
                "state": "region",
            }
        )
        df["name"] = df["name"] + " (Warehouse)"
        logger.info(f"Generated {len(df)} warehouses")
        return df

    def generate_products(
        self,
        n_products: int = 1000,
        supplier_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Generate pharmaceutical products dataset. If supplier_df is provided, adds supplier_id and use-case columns."""
        logger.info(f"Generating {n_products} products...")
        supplier_ids = (
            list(supplier_df["supplier_id"].values) if supplier_df is not None else []
        )

        data = []
        for _ in range(n_products):
            product_id = f"PROD_{self.fake.random_int(min=100000, max=999999)}"

            # Generate realistic pricing
            base_price = self.fake.random_int(min=5, max=500)
            is_prescription = self.fake.boolean(chance_of_getting_true=60)
            category = self.fake.pharma_category()
            manufacturer = f"{self.fake.company()} Pharmaceuticals"
            supplier_name = f"{self.fake.company()} Medical Supplies"

            row = {
                "product_id": product_id,
                "name": f"{self.fake.word().title()} {self.fake.word().title()} {self.fake.random_int(min=10, max=1000)}mg",
                "generic_name": f"{self.fake.word().title()} {self.fake.word().title()}",
                "category": category,
                "manufacturer": manufacturer,
                "supplier": supplier_name,
                "pbs_code": self.fake.pbs_code() if is_prescription else None,
                "atc_code": self.fake.atc_code(),
                "unit_price": base_price,
                "wholesale_price": base_price * 0.7,
                "retail_price": base_price * 1.3,
                "is_prescription": is_prescription,
                "is_controlled_substance": self.fake.boolean(
                    chance_of_getting_true=5
                ),
                "requires_cold_chain": self.fake.boolean(chance_of_getting_true=15),
                "storage_type": self.fake.storage_type(),
                "expiry_months": self.fake.random_int(min=12, max=60),
                "batch_size": self.fake.random_int(min=10, max=1000),
                "minimum_order_quantity": self.fake.random_int(min=1, max=50),
                "lead_time_days": self.fake.random_int(min=1, max=30),
                "active_ingredient": f"{self.fake.word().title()} {self.fake.random_int(min=1, max=1000)}mg",
                "dosage_form": self.fake.random_element(
                    ["Tablet", "Capsule", "Syrup", "Injection", "Cream", "Ointment"]
                ),
                "pack_size": f"{self.fake.random_int(min=10, max=1000)} {self.fake.random_element(['tablets', 'capsules', 'ml', 'g'])}",
                "created_date": self.fake.date_between(
                    start_date="-10y", end_date="today"
                ),
                "last_updated": self.fake.date_between(
                    start_date="-1y", end_date="today"
                ),
            }
            if supplier_ids:
                row["supplier_id"] = self.fake.random_element(supplier_ids)
                row["therapeutic_category"] = category
                row["brand"] = manufacturer
                row["generic_equivalent_id"] = (
                    self.fake.random_element([f"GEN_{self.fake.random_int(min=1, max=500)}"])
                    if self.fake.boolean(chance_of_getting_true=40)
                    else None
                )
                row["pack_size_variants"] = str(
                    self.fake.random_element([[28, 56], [30, 60, 90], [50, 100], [100]])
                )
                row["margin_percentage"] = round(
                    self.fake.random_int(min=5, max=35) + self.fake.random.random(), 2
                )
            data.append(row)

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} products")
        return df

    def generate_orders(
        self,
        n_orders: int = 5000,
        pharmacy_df: pd.DataFrame = None,
        hospital_df: pd.DataFrame = None,
        product_df: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """Generate orders dataset with foreign keys."""
        logger.info(f"Generating {n_orders} orders...")

        if pharmacy_df is None or hospital_df is None or product_df is None:
            raise ValueError(
                "pharmacy_df, hospital_df, and product_df must be provided"
            )

        data = []
        for _ in range(n_orders):
            # Randomly choose between pharmacy and hospital
            is_pharmacy = self.fake.boolean(chance_of_getting_true=80)

            if is_pharmacy:
                customer_id = self.fake.random_element(
                    pharmacy_df["pharmacy_id"].values
                )
                customer_type = "Pharmacy"
            else:
                customer_id = self.fake.random_element(
                    hospital_df["hospital_id"].values
                )
                customer_type = "Hospital"

            product_id = self.fake.random_element(product_df["product_id"].values)
            product_info = product_df[product_df["product_id"] == product_id].iloc[0]

            # Generate order details
            order_date = self.fake.date_between(start_date="-2y", end_date="today")
            quantity = self.fake.random_int(min=1, max=100)
            unit_price = product_info["wholesale_price"]
            total_amount = quantity * unit_price

            # Add some realistic business logic
            discount_rate = 0.0
            if quantity >= 50:
                discount_rate = self.fake.random_int(min=5, max=15) / 100
            elif quantity >= 20:
                discount_rate = self.fake.random_int(min=2, max=8) / 100

            discounted_amount = total_amount * (1 - discount_rate)

            data.append(
                {
                    "order_id": f"ORD_{self.fake.random_int(min=100000, max=999999)}",
                    "customer_id": customer_id,
                    "customer_type": customer_type,
                    "product_id": product_id,
                    "order_date": order_date,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_amount": total_amount,
                    "discount_rate": discount_rate,
                    "discounted_amount": discounted_amount,
                    "order_status": self.fake.random_element(
                        ["Pending", "Confirmed", "Shipped", "Delivered", "Cancelled"]
                    ),
                    "payment_terms": self.fake.random_element(
                        ["Net 30", "Net 15", "COD", "Prepaid"]
                    ),
                    "shipping_method": self.fake.random_element(
                        ["Standard", "Express", "Overnight", "Cold Chain"]
                    ),
                    "expected_delivery": order_date
                    + timedelta(days=self.fake.random_int(min=1, max=7)),
                    "actual_delivery": (
                        order_date + timedelta(days=self.fake.random_int(min=1, max=10))
                        if self.fake.boolean(chance_of_getting_true=90)
                        else None
                    ),
                    "special_instructions": (
                        self.fake.sentence()
                        if self.fake.boolean(chance_of_getting_true=20)
                        else None
                    ),
                    "sales_rep": self.fake.name(),
                    "created_timestamp": self.fake.date_time_between(
                        start_date="-2y", end_date="now"
                    ),
                }
            )

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} orders")
        return df

    def generate_inventory(
        self,
        n_records: int = 10000,
        pharmacy_df: pd.DataFrame = None,
        product_df: pd.DataFrame = None,
    ) -> pd.DataFrame:
        """Generate inventory tracking dataset."""
        logger.info(f"Generating {n_records} inventory records...")

        if pharmacy_df is None or product_df is None:
            raise ValueError("pharmacy_df and product_df must be provided")

        data = []
        for _ in range(n_records):
            pharmacy_id = self.fake.random_element(pharmacy_df["pharmacy_id"].values)
            product_id = self.fake.random_element(product_df["product_id"].values)
            product_info = product_df[product_df["product_id"] == product_id].iloc[0]

            # Generate inventory data
            current_stock = self.fake.random_int(min=0, max=500)
            reorder_level = self.fake.random_int(min=10, max=100)
            max_stock = self.fake.random_int(min=200, max=1000)

            # Calculate if reorder is needed
            needs_reorder = current_stock <= reorder_level

            data.append(
                {
                    "inventory_id": f"INV_{self.fake.random_int(min=100000, max=999999)}",
                    "pharmacy_id": pharmacy_id,
                    "product_id": product_id,
                    "current_stock": current_stock,
                    "reorder_level": reorder_level,
                    "max_stock": max_stock,
                    "needs_reorder": needs_reorder,
                    "last_restocked": self.fake.date_between(
                        start_date="-6m", end_date="today"
                    ),
                    "expiry_date": self.fake.date_between(
                        start_date="today", end_date="+2y"
                    ),
                    "batch_number": f"BATCH_{self.fake.random_int(min=10000, max=99999)}",
                    "storage_location": self.fake.random_element(
                        ["A1", "B2", "C3", "Cold Room", "Refrigerator"]
                    ),
                    "cost_per_unit": product_info["wholesale_price"],
                    "last_movement_date": self.fake.date_between(
                        start_date="-1m", end_date="today"
                    ),
                    "movement_type": self.fake.random_element(
                        ["In", "Out", "Transfer", "Adjustment"]
                    ),
                    "movement_quantity": self.fake.random_int(min=1, max=50),
                    "updated_timestamp": self.fake.date_time_between(
                        start_date="-1m", end_date="now"
                    ),
                }
            )

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} inventory records")
        return df

    def generate_supply_chain_events(
        self, n_events: int = 2000, order_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """Generate supply chain tracking events."""
        logger.info(f"Generating {n_events} supply chain events...")

        if order_df is None:
            raise ValueError("order_df must be provided")

        event_types = [
            "Order_Received",
            "Payment_Confirmed",
            "Picking_Started",
            "Picking_Completed",
            "Quality_Check",
            "Packaging",
            "Shipped",
            "In_Transit",
            "Out_for_Delivery",
            "Delivered",
            "Delivery_Failed",
            "Returned",
            "Damaged",
            "Lost",
        ]

        data = []
        for _ in range(n_events):
            order_id = self.fake.random_element(order_df["order_id"].values)
            event_type = self.fake.random_element(event_types)

            # Generate realistic event timing
            order_info = order_df[order_df["order_id"] == order_id].iloc[0]
            order_date = order_info["order_date"]

            # Event should be after order date
            event_date = self.fake.date_time_between(
                start_date=order_date, end_date=order_date + timedelta(days=30)
            )

            data.append(
                {
                    "event_id": f"EVT_{self.fake.random_int(min=100000, max=999999)}",
                    "order_id": order_id,
                    "event_type": event_type,
                    "event_timestamp": event_date,
                    "location": self.fake.city(),
                    "status": self.fake.random_element(
                        ["Success", "Warning", "Error", "Pending"]
                    ),
                    "description": f"{event_type.replace('_', ' ').title()} for order {order_id}",
                    "operator": self.fake.name(),
                    "equipment_id": f"EQ_{self.fake.random_int(min=1000, max=9999)}",
                    "temperature": (
                        self.fake.random_int(min=-20, max=25)
                        if "Cold" in event_type
                        else None
                    ),
                    "notes": (
                        self.fake.sentence()
                        if self.fake.boolean(chance_of_getting_true=30)
                        else None
                    ),
                }
            )

        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} supply chain events")
        return df

    def generate_product_interactions(
        self,
        order_df: pd.DataFrame,
        product_df: pd.DataFrame,
        pharmacy_df: pd.DataFrame,
        hospital_df: pd.DataFrame,
        n_extra: int = 5000,
    ) -> pd.DataFrame:
        """Generate product interactions (viewed, searched, added, purchased) for recommendation engine."""
        logger.info("Generating product_interactions...")
        data = []
        # Purchased from orders
        for _, row in order_df.iterrows():
            data.append(
                {
                    "interaction_id": f"INT_{uuid.uuid4().hex[:12].upper()}",
                    "customer_id": row["customer_id"],
                    "product_id": row["product_id"],
                    "action_type": "purchased",
                    "timestamp": row.get("created_timestamp", row["order_date"]),
                    "session_id": f"SES_{self.fake.random_int(min=100000, max=999999)}",
                }
            )
        # Synthetic viewed, searched, added
        customer_ids = list(pharmacy_df["pharmacy_id"].values) + list(
            hospital_df["hospital_id"].values
        )
        product_ids = list(product_df["product_id"].values)
        for _ in range(n_extra):
            action = self.fake.random_element(
                ["viewed", "searched", "added_to_cart"]
            )
            data.append(
                {
                    "interaction_id": f"INT_{uuid.uuid4().hex[:12].upper()}",
                    "customer_id": self.fake.random_element(customer_ids),
                    "product_id": self.fake.random_element(product_ids),
                    "action_type": action,
                    "timestamp": self.fake.date_time_between(
                        start_date="-1y", end_date="now"
                    ),
                    "session_id": f"SES_{self.fake.random_int(min=100000, max=999999)}",
                }
            )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} product_interactions")
        return df

    def generate_substitution_events(
        self,
        order_df: pd.DataFrame,
        product_df: pd.DataFrame,
        ratio: float = 0.1,
    ) -> pd.DataFrame:
        """Generate substitution events for a subset of orders (recommendation engine)."""
        logger.info("Generating substitution_events...")
        data = []
        product_ids = list(product_df["product_id"].values)
        sample = order_df.sample(
            frac=min(ratio, 1.0),
            random_state=42,
        )
        for _, row in sample.iterrows():
            requested = row["product_id"]
            substituted = self.fake.random_element(
                [p for p in product_ids if p != requested]
            )
            margin_delta = round(
                (self.fake.random_int(min=-10, max=15) / 100.0), 2
            )
            data.append(
                {
                    "substitution_id": f"SUB_{self.fake.random_int(min=100000, max=999999)}",
                    "order_id": row["order_id"],
                    "requested_product_id": requested,
                    "substituted_product_id": substituted,
                    "reason": self.fake.random_element(
                        ["out_of_stock", "generic_substitution", "therapeutic_alternative"]
                    ),
                    "customer_accepted": self.fake.boolean(chance_of_getting_true=85),
                    "margin_delta": margin_delta,
                    "timestamp": row.get("created_timestamp", row["order_date"]),
                }
            )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} substitution_events")
        return df

    def generate_inventory_availability(
        self,
        inventory_df: pd.DataFrame,
        product_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate inventory_availability (product x warehouse) for recommendation engine."""
        logger.info("Generating inventory_availability...")
        inv = inventory_df.copy()
        inv["warehouse_id"] = inv["pharmacy_id"]
        snapshot_date = self.fake.date_between(
            start_date="-30d", end_date="today"
        )
        agg = inv.groupby(["product_id", "warehouse_id"], as_index=False).agg(
            quantity_available=("current_stock", "sum")
        )
        prod = product_df.set_index("product_id")
        agg["lead_time_days"] = agg["product_id"].map(
            lambda p: prod.loc[p, "lead_time_days"] if p in prod.index else 7
        )
        agg["supplier_id"] = (
            agg["product_id"].map(
                lambda p: prod.loc[p, "supplier_id"]
                if "supplier_id" in prod.columns and p in prod.index
                else None
            )
            if "supplier_id" in product_df.columns
            else None
        )
        agg["snapshot_date"] = snapshot_date
        df = agg[
            [
                "product_id",
                "warehouse_id",
                "quantity_available",
                "lead_time_days",
                "supplier_id",
                "snapshot_date",
            ]
        ]
        logger.info(f"Generated {len(df)} inventory_availability rows")
        return df

    def generate_expiry_batches(
        self,
        inventory_df: pd.DataFrame,
        product_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate expiry_batches from inventory (inventory optimisation)."""
        logger.info("Generating expiry_batches...")
        inv = inventory_df.copy()
        inv["warehouse_id"] = inv["pharmacy_id"]
        inv["batch_id"] = inv["batch_number"]
        inv["cost_basis"] = inv.get("cost_per_unit", 0) * inv.get(
            "movement_quantity", inv["current_stock"]
        )
        df = inv[
            [
                "batch_id",
                "product_id",
                "warehouse_id",
                "expiry_date",
                "current_stock",
                "cost_basis",
            ]
        ].copy()
        df = df.rename(columns={"current_stock": "quantity"})
        logger.info(f"Generated {len(df)} expiry_batches")
        return df

    def generate_writeoff_events(
        self,
        n_events: int,
        product_df: pd.DataFrame,
        warehouse_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate writeoff_events (expired, damaged, obsolete)."""
        logger.info(f"Generating {n_events} writeoff_events...")
        data = []
        for _ in range(n_events):
            product_id = self.fake.random_element(product_df["product_id"].values)
            warehouse_id = self.fake.random_element(
                warehouse_df["warehouse_id"].values
            )
            cost = float(
                product_df[product_df["product_id"] == product_id][
                    "wholesale_price"
                ].iloc[0]
            )
            qty = self.fake.random_int(min=1, max=50)
            data.append(
                {
                    "event_id": f"WO_{self.fake.random_int(min=100000, max=999999)}",
                    "product_id": product_id,
                    "warehouse_id": warehouse_id,
                    "quantity": qty,
                    "reason": self.fake.random_element(
                        ["expired", "damaged", "obsolete"]
                    ),
                    "cost": round(cost * qty, 2),
                    "timestamp": self.fake.date_time_between(
                        start_date="-1y", end_date="now"
                    ),
                }
            )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} writeoff_events")
        return df

    def generate_purchase_orders(
        self,
        n_orders: int,
        supplier_df: pd.DataFrame,
        product_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate purchase_orders (inventory optimisation)."""
        logger.info(f"Generating {n_orders} purchase_orders...")
        data = []
        for _ in range(n_orders):
            supplier_id = self.fake.random_element(
                supplier_df["supplier_id"].values
            )
            product_id = self.fake.random_element(
                product_df["product_id"].values
            )
            unit_cost = float(
                product_df[product_df["product_id"] == product_id][
                    "wholesale_price"
                ].iloc[0]
            )
            lead = int(
                supplier_df[supplier_df["supplier_id"] == supplier_id][
                    "lead_time_days"
                ].iloc[0]
            )
            order_date = self.fake.date_between(start_date="-1y", end_date="today")
            expected = order_date + timedelta(days=lead)
            actual = (
                expected + timedelta(days=self.fake.random_int(min=-2, max=5))
                if self.fake.boolean(chance_of_getting_true=90)
                else None
            )
            data.append(
                {
                    "po_id": f"PO_{self.fake.random_int(min=100000, max=999999)}",
                    "supplier_id": supplier_id,
                    "product_id": product_id,
                    "quantity": self.fake.random_int(min=10, max=500),
                    "order_date": order_date,
                    "expected_delivery_date": expected,
                    "actual_delivery_date": actual,
                    "unit_cost": round(unit_cost, 2),
                }
            )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} purchase_orders")
        return df

    def generate_supplier_performance(
        self,
        supplier_df: pd.DataFrame,
        product_df: pd.DataFrame,
        purchase_order_df: pd.DataFrame,
        n_months: int = 12,
    ) -> pd.DataFrame:
        """Generate supplier_performance (fill rate, lead time stats by month)."""
        logger.info("Generating supplier_performance...")
        data = []
        for supplier_id in supplier_df["supplier_id"].values[:50]:
            for _, prod in product_df.sample(n=min(5, len(product_df))).iterrows():
                for m in range(n_months):
                    data.append(
                        {
                            "supplier_id": supplier_id,
                            "product_id": prod["product_id"],
                            "fill_rate": round(
                                self.fake.random.random() * 0.2 + 0.8, 2
                            ),
                            "avg_lead_time_days": self.fake.random_int(
                                min=3, max=14
                            ),
                            "lead_time_std": round(
                                self.fake.random.random() * 3 + 0.5, 2
                            ),
                            "month": (date.today() - timedelta(days=30 * (n_months - m))).replace(day=1),
                        }
                    )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} supplier_performance rows")
        return df

    def generate_warehouse_costs(
        self,
        warehouse_df: pd.DataFrame,
        product_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate warehouse_costs (storage + handling by warehouse x product)."""
        logger.info("Generating warehouse_costs...")
        data = []
        for _, wh in warehouse_df.iterrows():
            for _, prod in product_df.sample(n=min(20, len(product_df))).iterrows():
                data.append(
                    {
                        "warehouse_id": wh["warehouse_id"],
                        "product_id": prod["product_id"],
                        "storage_cost": round(
                            self.fake.random.random() * 50 + 5, 2
                        ),
                        "handling_cost": round(
                            self.fake.random.random() * 20 + 2, 2
                        ),
                        "period": self.fake.date_between(
                            start_date="-3m", end_date="today"
                        ).replace(day=1),
                    }
                )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} warehouse_costs rows")
        return df

    def generate_competitor_products(self, n: int = 200) -> pd.DataFrame:
        """Generate competitor_products (synthetic pricing data for insights)."""
        logger.info(f"Generating {n} competitor_products...")
        data = []
        for _ in range(n):
            data.append(
                {
                    "competitor_id": f"CMP_{self.fake.random_int(min=1, max=20)}",
                    "product_name": f"{self.fake.word().title()} {self.fake.random_int(min=10, max=500)}mg",
                    "price": round(
                        self.fake.random_int(min=5, max=400)
                        + self.fake.random.random(),
                        2,
                    ),
                    "url": f"https://competitor.com/p/{uuid.uuid4().hex[:8]}",
                    "scrape_date": self.fake.date_between(
                        start_date="-30d", end_date="today"
                    ),
                }
            )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} competitor_products")
        return df

    def generate_competitor_price_history(
        self,
        competitor_products_df: pd.DataFrame,
        n_weeks: int = 12,
    ) -> pd.DataFrame:
        """Generate competitor_price_history time series (one row per product per week)."""
        logger.info("Generating competitor_price_history...")
        data = []
        for _, row in competitor_products_df.iterrows():
            base_price = row["price"]
            for w in range(n_weeks):
                dt = self.fake.date_between(
                    start_date=f"-{n_weeks * 7}d", end_date="today"
                )
                data.append(
                    {
                        "competitor_id": row["competitor_id"],
                        "product_name": row["product_name"],
                        "price": round(
                            base_price
                            * (1 + (self.fake.random.random() - 0.5) * 0.1),
                            2,
                        ),
                        "date": dt,
                    }
                )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} competitor_price_history rows")
        return df

    def generate_store_sales(
        self,
        pharmacy_df: pd.DataFrame,
        product_df: pd.DataFrame,
        n_days: int = 90,
    ) -> pd.DataFrame:
        """Generate store_sales (store_id = pharmacy_id) for insights."""
        logger.info("Generating store_sales...")
        data = []
        for _, ph in pharmacy_df.iterrows():
            for _, prod in product_df.sample(
                n=min(30, len(product_df))
            ).iterrows():
                for _ in range(max(1, min(10, n_days))):
                    dt = self.fake.date_between(
                        start_date=f"-{n_days}d", end_date="today"
                    )
                    qty = self.fake.random_int(min=1, max=20)
                    rev = qty * float(prod["retail_price"])
                    data.append(
                        {
                            "store_id": ph["pharmacy_id"],
                            "product_id": prod["product_id"],
                            "date": dt,
                            "sales_quantity": qty,
                            "revenue": round(rev, 2),
                        }
                    )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} store_sales rows")
        return df

    def generate_store_attributes(
        self, pharmacy_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Generate store_attributes (store_id = pharmacy_id)."""
        logger.info("Generating store_attributes...")
        df = pharmacy_df[["pharmacy_id", "address", "state"]].copy()
        df = df.rename(
            columns={
                "pharmacy_id": "store_id",
                "address": "location",
                "state": "region",
            }
        )
        df["size_sqm"] = [
            self.fake.random_int(min=50, max=300) for _ in range(len(df))
        ]
        df["store_type"] = "pharmacy"
        df["cluster_id"] = df["region"].map(
            lambda r: {"NSW": "C1", "VIC": "C1", "QLD": "C2", "WA": "C2", "SA": "C3", "TAS": "C3", "ACT": "C1", "NT": "C2"}.get(
                r, "C1"
            )
        )
        logger.info(f"Generated {len(df)} store_attributes")
        return df

    def generate_promotions(
        self,
        n: int,
        pharmacy_df: pd.DataFrame,
        product_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generate promotions (store_id = pharmacy_id)."""
        logger.info(f"Generating {n} promotions...")
        data = []
        store_ids = list(pharmacy_df["pharmacy_id"].values)
        product_ids = list(product_df["product_id"].values)
        for i in range(n):
            start = self.fake.date_between(
                start_date="-6m", end_date="today"
            )
            end = start + timedelta(days=self.fake.random_int(min=7, max=60))
            data.append(
                {
                    "promo_id": f"PROMO_{self.fake.random_int(min=10000, max=99999)}",
                    "store_id": self.fake.random_element(store_ids),
                    "product_id": self.fake.random_element(product_ids),
                    "start_date": start,
                    "end_date": end,
                    "discount_rate": round(
                        self.fake.random_int(min=5, max=30) / 100.0, 2
                    ),
                }
            )
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} promotions")
        return df

    def generate_all_datasets(
        self,
        n_pharmacies: int = 100,
        n_hospitals: int = 50,
        n_suppliers: int = 80,
        n_products: int = 1000,
        n_orders: int = 5000,
        n_inventory: int = 10000,
        n_events: int = 2000,
        n_product_interactions_extra: int = 5000,
        substitution_ratio: float = 0.1,
        n_purchase_orders: int = 3000,
        n_writeoff_events: int = 500,
        n_competitor_products: int = 200,
        store_sales_days: int = 90,
        n_promotions: int = 200,
    ) -> Dict[str, pd.DataFrame]:
        """Generate all datasets (base + use-case tables) with proper relationships."""
        logger.info("Generating complete healthcare dataset...")

        # Foundation
        pharmacies = self.generate_pharmacies(n_pharmacies)
        hospitals = self.generate_hospitals(n_hospitals)
        suppliers = self.generate_suppliers(n_suppliers)
        warehouses = self.generate_warehouses(pharmacies)
        products = self.generate_products(n_products, supplier_df=suppliers)

        # Base transactional
        orders = self.generate_orders(n_orders, pharmacies, hospitals, products)
        inventory = self.generate_inventory(n_inventory, pharmacies, products)
        events = self.generate_supply_chain_events(n_events, orders)

        # Recommendation Engine
        product_interactions = self.generate_product_interactions(
            orders, products, pharmacies, hospitals, n_extra=n_product_interactions_extra
        )
        substitution_events = self.generate_substitution_events(
            orders, products, ratio=substitution_ratio
        )
        inventory_availability = self.generate_inventory_availability(
            inventory, products
        )

        # Inventory Optimisation
        expiry_batches = self.generate_expiry_batches(inventory, products)
        writeoff_events = self.generate_writeoff_events(
            n_writeoff_events, products, warehouses
        )
        purchase_orders = self.generate_purchase_orders(
            n_purchase_orders, suppliers, products
        )
        supplier_performance = self.generate_supplier_performance(
            suppliers, products, purchase_orders
        )

        # Insights & Analytics
        warehouse_costs = self.generate_warehouse_costs(warehouses, products)
        competitor_products = self.generate_competitor_products(n_competitor_products)
        competitor_price_history = self.generate_competitor_price_history(
            competitor_products, n_weeks=12
        )
        store_sales = self.generate_store_sales(
            pharmacies, products, n_days=store_sales_days
        )
        store_attributes = self.generate_store_attributes(pharmacies)
        promotions = self.generate_promotions(
            n_promotions, pharmacies, products
        )

        datasets = {
            "pharmacies": pharmacies,
            "hospitals": hospitals,
            "suppliers": suppliers,
            "warehouses": warehouses,
            "products": products,
            "orders": orders,
            "inventory": inventory,
            "supply_chain_events": events,
            "product_interactions": product_interactions,
            "substitution_events": substitution_events,
            "inventory_availability": inventory_availability,
            "expiry_batches": expiry_batches,
            "writeoff_events": writeoff_events,
            "purchase_orders": purchase_orders,
            "supplier_performance": supplier_performance,
            "warehouse_costs": warehouse_costs,
            "competitor_products": competitor_products,
            "competitor_price_history": competitor_price_history,
            "store_sales": store_sales,
            "store_attributes": store_attributes,
            "promotions": promotions,
        }

        logger.info("Dataset generation completed successfully!")
        return datasets

    def save_datasets(
        self, datasets: Dict[str, pd.DataFrame], output_dir: str = "data"
    ) -> None:
        """Save datasets to CSV files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        logger.info(f"Saving datasets to {output_path}...")

        for name, df in datasets.items():
            file_path = output_path / f"{name}.csv"
            df.to_csv(file_path, index=False)
            logger.info(f"Saved {name}: {len(df)} records to {file_path}")

        logger.info("All datasets saved successfully!")


def main():
    """Main function to demonstrate data generation."""
    # Initialize generator with seed for reproducibility
    generator = HealthcareDataGenerator(seed=42)

    # Generate all datasets (base + use-case tables)
    datasets = generator.generate_all_datasets(
        n_pharmacies=50,
        n_hospitals=25,
        n_suppliers=40,
        n_products=500,
        n_orders=2000,
        n_inventory=5000,
        n_events=1000,
        n_product_interactions_extra=2000,
        substitution_ratio=0.1,
        n_purchase_orders=500,
        n_writeoff_events=100,
        n_competitor_products=50,
        store_sales_days=90,
        n_promotions=50,
    )

    # Display basic info about each dataset
    print("\n" + "=" * 60)
    print("HEALTHCARE DATASET SUMMARY")
    print("=" * 60)

    for name, df in datasets.items():
        print(f"\n{name.upper()}:")
        print(f"  Records: {len(df):,}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        print(f"  Sample columns: {list(df.columns[:5])}")

    # Show sample data
    print(f"\n{'='*60}")
    print("SAMPLE DATA - ORDERS")
    print("=" * 60)
    print(datasets["orders"].head())

    print(f"\n{'='*60}")
    print("SAMPLE DATA - PRODUCTS")
    print("=" * 60)
    print(
        datasets["products"][
            ["product_id", "name", "category", "unit_price", "is_prescription"]
        ].head()
    )

    # Save datasets
    generator.save_datasets(datasets)

    return datasets


if __name__ == "__main__":
    datasets = main()
