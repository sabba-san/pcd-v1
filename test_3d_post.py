import requests

s = requests.Session()

# The UI sends a JSON payload for new defects
payload = {
    "description": "Crack on the wall",
    "defect_type": "Crack",
    "severity": "High",
    "status": "Reported",
    "x": 10.5,
    "y": -2.3,
    "z": 5.1
}

resp = s.post("http://localhost:5000/module3/api/scans/1/defects", json=payload)
print("Response POST status:", resp.status_code)

if resp.status_code != 200 and resp.status_code != 201:
    print("Failed body:", resp.text)
else:
    print("New defect saved!")
