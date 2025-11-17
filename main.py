import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List
from datetime import datetime

app = FastAPI(title="Barber Shop Morocco API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Morocco Barber API running"}

@app.get("/api/hello")
def hello():
    return {"message": "Welcome to the Moroccan Barber backend!"}

@app.get("/api/services")
def list_services() -> List[Dict[str, Any]]:
    return [
        {"id": "cut", "name": "Classic Cut", "price": 120, "duration": 30, "desc": "Precision haircut tailored to your style."},
        {"id": "beard", "name": "Beard Trim", "price": 80, "duration": 20, "desc": "Clean lines and shape with hot towel finish."},
        {"id": "combo", "name": "Cut + Beard", "price": 180, "duration": 60, "desc": "Complete grooming session."},
        {"id": "fade", "name": "Skin Fade", "price": 140, "duration": 45, "desc": "Sharp fade with detailed finish."},
    ]

@app.get("/api/shop")
def shop_info() -> Dict[str, Any]:
    return {
        "name": "Zellige Barber",
        "tagline": "Crafted Cuts • Moroccan Soul",
        "address": "Rue Bab Doukkala, Marrakech, Morocco",
        "phone": "+212 6 12 34 56 78",
        "hours": {
            "mon_fri": "10:00 - 20:00",
            "sat": "10:00 - 18:00",
            "sun": "Closed"
        }
    }

# Database booking models
class BookingIn(BaseModel):
    name: str
    phone: str
    email: str | None = None
    service: str
    preferred_date: str | None = None
    preferred_time: str | None = None
    notes: str | None = None


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Mongo types (ObjectId, datetime) to JSON serializable values."""
    out: Dict[str, Any] = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@app.post("/api/bookings")
def create_booking(payload: BookingIn) -> Dict[str, Any]:
    try:
        from database import create_document
        from schemas import Booking as BookingSchema

        # Validate with full schema (enforces lengths and formats)
        booking = BookingSchema(**payload.model_dump())
        inserted_id = create_document("booking", booking)
        return {"status": "ok", "id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bookings")
def list_bookings() -> Dict[str, Any]:
    """Return recent bookings for admin view."""
    try:
        from database import get_documents
        docs = get_documents("booking", {}, limit=200)
        items = [_serialize_doc(d) for d in docs]
        # Sort by created_at desc if present
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.get("/schema")
def get_schema():
    """Expose Pydantic schemas for the database viewer/tools."""
    try:
        import schemas as s
        return {
            "booking": s.Booking.model_json_schema(),
            "user": s.User.model_json_schema(),
            "product": s.Product.model_json_schema(),
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
