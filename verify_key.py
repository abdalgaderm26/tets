import requests
import json

key = "AIzaSyBANNn8byDuYUXpc6cIDdCKXCKuFITfcmk"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"

try:
    response = requests.get(url)
    data = response.json()
    if 'models' in data:
        print("✅ API Key is Valid!")
        print("Available Models:")
        for m in data['models']:
            print(f"- {m['name']}")
    else:
        print("❌ API Key Error:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"❌ Connection Error: {str(e)}")
