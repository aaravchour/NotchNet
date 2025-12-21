import requests
import json
import sys

# Simulates the Java mod sending a list of mods
API_URL = "http://localhost:8000/admin/detect-mods"

payload = {
    "mods": [
        "fabric-api", 
        "sodium", 
        "create", 
        "jei", 
        "rlcraft" # RLCraft is a modpack, but sometimes "mod" name appears. 
        # Actually RLCraft usually isn't a single mod ID, but for testing our 'known wikis' map:
    ]
}

print(f"🚀 Sending payload to {API_URL}: {json.dumps(payload, indent=2)}")

try:
    resp = requests.post(API_URL, json=payload, headers={"X-Internal-Secret": "SuperSecretInternalKey123"})
    print(f"Response ({resp.status_code}):")
    print(resp.text)
except Exception as e:
    print(f"❌ Error: {e}")
