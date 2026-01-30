
from tools.search_hotels import search_hotels
import json

def check():
    print("Running search_hotels...")
    # Mock payload
    res = search_hotels(payload={"location": "Maldives", "check_in": "2024-01-01"})
    try:
        data = json.loads(res)
        print(f"Status: {data.get('status')}")
        print(f"Search Type: {data.get('search_type')}")
        items = data.get('data', [])
        print(f"Count: {len(items)}")
        
        if data.get('search_type') == 'HOTEL' and len(items) <= 10:
            print("✅ check_types Passed")
        else:
            print("❌ check_types Failed")
            
    except Exception as e:
        print(f"Error parsing json: {e}")

if __name__ == "__main__":
    check()
