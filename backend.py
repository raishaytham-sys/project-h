from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INTERVALS_API_KEY = "3f1cwe6lade0tfoupus7uj85z"
ATHLETE_ID = "i586352"
AUTH = ("API_KEY", INTERVALS_API_KEY)
BASE_URL = "https://intervals.icu/api/v1"

TYPE_MAP = {
    "run": ["Run", "VirtualRun", "TrailRun"],
    "hike": ["Hike"],
    "all": None
}

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/api/activities")
def get_activities(type: str = "all", weeks: int = 24):
    oldest = (datetime.now() - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    newest = datetime.now().strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/athlete/{ATHLETE_ID}/activities"
    params = {"oldest": oldest, "newest": newest}
    
    response = requests.get(url, auth=AUTH, params=params)
    activities = response.json()
    
    allowed_types = TYPE_MAP.get(type)
    if allowed_types:
        activities = [a for a in activities if a.get("type") in allowed_types]
    
    return activities

@app.get("/api/activity/{activity_id}/streams")
def get_streams(activity_id: str):
    url = f"{BASE_URL}/activity/{activity_id}/streams"
    params = {"types": "time,latlng,altitude,heartrate,distance,velocity_smooth,watts,cadence"}
    response = requests.get(url, auth=AUTH, params=params)
    normalized = {"latlng": [], "altitude": [], "heartrate": [], "distance": [], "time": [], "watts": [], "velocity_smooth": []}

    print(f"[streams] {activity_id} — HTTP {response.status_code}, body length: {len(response.text)}")

    if not response.text.strip():
        print(f"[streams] {activity_id} — réponse vide")
        return normalized

    try:
        raw = response.json()
    except Exception as e:
        print(f"[streams] {activity_id} — JSON decode error: {e}, body: {response.text[:200]}")
        return normalized

    if isinstance(raw, list):
        for item in raw:
            key = item.get("type")
            if key in normalized:
                normalized[key] = item.get("data", [])
    elif isinstance(raw, dict):
        for key in normalized:
            if key in raw:
                normalized[key] = raw[key]

    print(f"[streams] {activity_id} — keys présentes: {[k for k,v in normalized.items() if v]}")
    return normalized

@app.get("/api/activity/{activity_id}")
def get_activity_detail(activity_id: str):
    url = f"{BASE_URL}/activity/{activity_id}"
    response = requests.get(url, auth=AUTH)
    return response.json()
