import requests

token = input("Token RMS : ").strip()
base  = "https://api.rms.teltonika-networks.com"

# Test offset-based pagination
for offset in [0, 100, 200]:
    resp = requests.get(
        f"{base}/devices",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 100, "offset": offset},
        timeout=15
    )
    body  = resp.json()
    data  = body.get("data", [])
    meta  = body.get("meta", {})
    first = data[0].get("serial") if data else "vide"
    print(f"offset={offset} → {len(data)} devices | premier SN: {first} | meta: {meta}")
