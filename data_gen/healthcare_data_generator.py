"""
Healthcare Data Generator for EBOS-style pharmaceutical distribution scenarios.

This module generates synthetic datasets for healthcare/pharmaceutical distribution
including pharmacies, hospitals, products, orders, and supply chain data.
"""

import random
from datetime import timedelta
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
    "products": 1000,
    "orders": 5000,
    "inventory": 10000,
    "events": 2000,
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

    def generate_products(self, n_products: int = 1000) -> pd.DataFrame:
        """Generate pharmaceutical products dataset."""
        logger.info(f"Generating {n_products} products...")

        data = []
        for _ in range(n_products):
            product_id = f"PROD_{self.fake.random_int(min=100000, max=999999)}"

            # Generate realistic pricing
            base_price = self.fake.random_int(min=5, max=500)
            is_prescription = self.fake.boolean(chance_of_getting_true=60)

            data.append(
                {
                    "product_id": product_id,
                    "name": f"{self.fake.word().title()} {self.fake.word().title()} {self.fake.random_int(min=10, max=1000)}mg",
                    "generic_name": f"{self.fake.word().title()} {self.fake.word().title()}",
                    "category": self.fake.pharma_category(),
                    "manufacturer": f"{self.fake.company()} Pharmaceuticals",
                    "supplier": f"{self.fake.company()} Medical Supplies",
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
            )

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

    def generate_all_datasets(
        self,
        n_pharmacies: int = 100,
        n_hospitals: int = 50,
        n_products: int = 1000,
        n_orders: int = 5000,
        n_inventory: int = 10000,
        n_events: int = 2000,
    ) -> Dict[str, pd.DataFrame]:
        """Generate all datasets with proper relationships."""
        logger.info("Generating complete healthcare dataset...")

        # Generate base datasets
        pharmacies = self.generate_pharmacies(n_pharmacies)
        hospitals = self.generate_hospitals(n_hospitals)
        products = self.generate_products(n_products)

        # Generate dependent datasets
        orders = self.generate_orders(n_orders, pharmacies, hospitals, products)
        inventory = self.generate_inventory(n_inventory, pharmacies, products)
        events = self.generate_supply_chain_events(n_events, orders)

        datasets = {
            "pharmacies": pharmacies,
            "hospitals": hospitals,
            "products": products,
            "orders": orders,
            "inventory": inventory,
            "supply_chain_events": events,
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

    # Generate all datasets
    datasets = generator.generate_all_datasets(
        n_pharmacies=50,
        n_hospitals=25,
        n_products=500,
        n_orders=2000,
        n_inventory=5000,
        n_events=1000,
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
