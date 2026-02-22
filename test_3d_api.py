import requests

# We'll use a session to establish dummy cookies since it requires login
s = requests.Session()

# Needs an active user to submit. We'll simulate checking the endpoint. 
# We'll run this to just test for 500s or 401s
resp = s.get("http://localhost:5000/module3/api/scans/1/defects")
print("Response GET:", resp.status_code)
