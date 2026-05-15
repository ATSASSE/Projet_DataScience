# Mini script pour tester quel parametre de pagination RMS accepte
import requests, sys

token = input("Token RMS : ").strip()
base  = "https://api.rms.teltonika-networks.com"

for params in [
    {"page": 1, "per_page": 500},
    {"page": 1, "limit": 500},
    {"page": 1, "page[size]": 500},
    {"page": 1, "count": 500},
    {"page": 1, "rows": 500},
]:
    resp = requests.get(f"{base}/devices", headers={"Authorization": f"Bearer {token}"}, params=params, timeout=15)
    body = resp.json()
    count = len(body.get("data", []))
    meta  = body.get("meta", {})
    print(f"params={params} → {count} devices | meta={meta}")
