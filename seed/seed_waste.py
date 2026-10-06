"""Seed the waste_logs collection with realistic, reproducible sample data."""
import random
from datetime import datetime, timedelta

from db.mongo_conn import get_collection

random.seed(42)                    # same "random" data on every laptop
N_LOGS = 240
START = datetime(2026, 6, 1)       # fixed window: 1 Jun to 30 Sep
DAYS = 122

KG_PER_UNIT = {"kg": 1.0, "plates": 0.4, "packets": 0.25}   # mirrors unit_conversions

# category_id: (name, items, unit, (min_qty, max_qty), reason weights, Rs per kg, storage)
CATEGORIES = {
    1: ("Cooked Meals", ["Veg biryani", "Dal tadka", "Paneer curry", "Chapati"],
        "plates", (10, 60), {"Overproduction": 5, "Plate Waste": 3, "Spoiled": 1, "Expired": 1}, 150, "Hot"),
    2: ("Bakery Items", ["Bread loaves", "Croissants", "Muffins", "Pav buns"],
        "packets", (5, 40), {"Unsold": 6, "Expired": 3, "Overproduction": 1}, 200, "Ambient"),
    3: ("Dairy Products", ["Milk", "Paneer", "Curd", "Cream"],
        "kg", (2, 15), {"Expired": 5, "Spoiled": 4}, 120, "Cold"),
    4: ("Fruits & Vegetables", ["Tomatoes", "Spinach", "Bananas", "Onions"],
        "kg", (3, 25), {"Spoiled": 6, "Expired": 2, "Unsold": 2}, 40, "Ambient"),
    5: ("Packaged Food", ["Biscuit packs", "Chips", "Instant noodles"],
        "packets", (10, 80), {"Expired": 6, "Unsold": 3}, 180, "Ambient"),
    6: ("Beverages", ["Fruit juice", "Lassi", "Buttermilk"],
        "kg", (2, 20), {"Unsold": 4, "Expired": 4, "Overproduction": 2}, 80, "Cold"),
    7: ("Rice & Grains (Cooked)", ["Steamed rice", "Jeera rice", "Khichdi"],
        "plates", (15, 80), {"Overproduction": 5, "Plate Waste": 4, "Spoiled": 1}, 70, "Hot"),
    8: ("Sweets & Desserts", ["Gulab jamun", "Kheer", "Ice cream", "Cake slices"],
        "kg", (1, 10), {"Unsold": 4, "Expired": 3, "Spoiled": 3}, 300, "Cold"),
}

# Unequal weights so some donors waste far more than others
DONOR_WEIGHTS = {1: 3, 2: 2, 3: 6, 4: 3, 5: 5, 6: 1, 7: 4, 8: 2}

NOTES = ["Event cancelled at short notice", "Power cut affected storage",
         "Over-ordered for the weekend", "Delivery arrived late",
         "Footfall lower than expected"]


def make_log():
    donor_id = random.choices(list(DONOR_WEIGHTS), weights=list(DONOR_WEIGHTS.values()))[0]
    category_id = random.choice(list(CATEGORIES))
    name, items, unit, (lo, hi), reasons, cost_per_kg, storage = CATEGORIES[category_id]

    quantity = round(random.uniform(lo, hi), 1) if unit == "kg" else random.randint(lo, hi)
    qty_kg = round(quantity * KG_PER_UNIT[unit], 2)
    when = START + timedelta(days=random.randrange(DAYS),
                             hours=random.randint(8, 22),
                             minutes=random.randint(0, 59))

    doc = {
        "donor_id": donor_id,
        "category_id": category_id,
        "category": name,
        "item": random.choice(items),
        "quantity": quantity,
        "unit": unit,
        "qty_kg": qty_kg,
        "reason": random.choices(list(reasons), weights=list(reasons.values()))[0],
        "recorded_at": when,                       # a real datetime, not a string
        "estimated_cost": round(qty_kg * cost_per_kg * random.uniform(0.8, 1.2), 2),
        "seeded": True,                            # marks sample data
    }
    # Optional fields: only some logs have them (the flexibility MySQL doesn't give you)
    if random.random() < 0.4:
        doc["notes"] = random.choice(NOTES)
    if random.random() < 0.5:
        doc["storage_condition"] = storage
    return doc


def main():
    logs = get_collection("waste_logs")
    removed = logs.delete_many({"seeded": True}).deleted_count
    docs = [make_log() for _ in range(N_LOGS)]
    logs.insert_many(docs)
    print(f"Removed {removed} old seed logs, inserted {len(docs)} new ones.")
    print("Total documents in waste_logs:", logs.count_documents({}))


if __name__ == "__main__":
    main()