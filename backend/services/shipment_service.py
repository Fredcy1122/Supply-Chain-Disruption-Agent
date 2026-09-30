import os
import pandas as pd
from fastapi import HTTPException
from backend.models.schemas import ShipmentResponse

# Resolve the absolute path to the data folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "dataco_supply_chain.csv")

# Load data into memory once when the server starts
try:
    df = pd.read_csv(DATA_PATH, low_memory=False)
    # Ensure IDs are strings for clean matching
    df['Order Id'] = df['Order Id'].astype(str)
    print(f"✅ Successfully loaded {len(df)} records from DataCo dataset.")
except FileNotFoundError:
    df = pd.DataFrame()
    print("⚠️ DataCo dataset not found at backend/data/. Falling back to mock data.")

def get_shipment_by_id(shipment_id: str) -> ShipmentResponse:
    """
    Looks up a shipment in the DataCo dataset and maps it to the Pydantic schema.
    """
    # 1. Try to fetch from the real dataset if it exists
    if not df.empty:
        match = df[df['Order Id'] == shipment_id]
        if not match.empty:
            row = match.iloc[0]
            return ShipmentResponse(
                shipment_id=shipment_id,
                product_category=str(row.get('Category Name', 'Unknown')),
                destination=f"{row.get('Order City', 'Unknown')}, {row.get('Order Country', 'Unknown')}",
                shipping_mode=str(row.get('Shipping Mode', 'Standard Class')),
                days_for_shipping_real=float(row.get('Days for shipping (real)', 0.0)),
                days_for_shipment_scheduled=float(row.get('Days for shipment (scheduled)', 0.0)),
                current_status=str(row.get('Delivery Status', 'Pending'))
            )
            
    # 2. Fallback mechanism for local testing without the massive CSV
    if "safe" in shipment_id.lower() or df.empty or shipment_id == "SHP001":
        return ShipmentResponse(
            shipment_id=shipment_id,
            product_category="Electronics",
            destination="Kajola, Osun",
            shipping_mode="First Class",
            days_for_shipping_real=None,
            days_for_shipment_scheduled=5.0,
            current_status="In Transit"
        )
        
    # 3. If data exists but the ID is totally invalid
    raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found in database.")