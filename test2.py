import requests

response = requests.post("http://127.0.0.1:5001/api/v0/version")

if response.status_code == 200:
    print("IPFS Version:", response.json())
else:
    print("Error:", response.text)
