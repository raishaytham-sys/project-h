from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests
import xml.etree.ElementTree as ET
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

def extract_gpx_coords(gpx_text):
    try:
        root = ET.fromstring(gpx_text)
        coords = []
        for pt in root.findall('.//{*}trkpt'):
            coords.append([float(pt.get('lat')), float(pt.get('lon'))])
        return coords
    except Exception as e:
        print(f"[GPX parse error] {e}")
        return []

@app.get("/api/activity/{activity_id}/streams")
def get_streams(activity_id: str):
    url = f"{BASE_URL}/activity/{activity_id}/streams"
    params = {"types": "time,latlng,altitude,heartrate,distance,velocity_smooth,watts,cadence"}
    response = requests.get(url, auth=AUTH, params=params)
    raw = response.json() if response.status_code == 200 else {}
    if isinstance(raw, list):
        result = {}
        for item in raw:
            if 'type' not in item or 'data' not in item:
                continue
            key = item['type']
            if key == 'latlng' and item.get('data2'):
                lats = item['data']
                lngs = item['data2']
                result[key] = [
                    [lats[i], lngs[i]]
                    for i in range(min(len(lats), len(lngs)))
                    if lats[i] is not None and lngs[i] is not None
                ]
            else:
                result[key] = item['data']
    elif isinstance(raw, dict):
        result = raw
    else:
        result = {}
    for key in ['latlng','altitude','heartrate','distance','time','velocity_smooth','watts','cadence']:
        if key not in result:
            result[key] = []
    print(f"[streams] {activity_id} — keys: {[k for k,v in result.items() if v]}")
    if not result.get('latlng'):
        try:
            gpx_resp = requests.get(f"{BASE_URL}/activity/{activity_id}/gpx", auth=AUTH)
            print(f"[GPX] status={gpx_resp.status_code} len={len(gpx_resp.text)}")
            if gpx_resp.status_code == 200 and len(gpx_resp.text) > 100:
                coords = extract_gpx_coords(gpx_resp.text)
                print(f"[GPX] coords parsed: {len(coords)}")
                if coords:
                    result['latlng'] = coords
            if not result.get('latlng'):
                fit_resp = requests.get(
                    f"https://intervals.icu/api/v1/activity/{activity_id}/fit",
                    auth=AUTH
                )
                print(f"[FIT] status={fit_resp.status_code}")
        except Exception as e:
            print(f"[GPX fallback error] {e}")
    return result

@app.get("/api/activity/{activity_id}")
def get_activity_detail(activity_id: str):
    url = f"{BASE_URL}/activity/{activity_id}"
    response = requests.get(url, auth=AUTH)
    return response.json()
