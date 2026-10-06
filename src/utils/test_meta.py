import os
import requests

BASE_IG = "https://graph.instagram.com/v26.0"
BASE_FB = "https://graph.facebook.com/v26.0"
ok = True

ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
if ig_token:
    r = requests.get(
        f"{BASE_IG}/me",
        params={"fields": "username", "access_token": ig_token},
        timeout=30,
    )
    print("INSTAGRAM:", r.status_code, r.text)
    ok = ok and r.ok
else:
    print("INSTAGRAM: skipped (no token)")

page_token = os.environ.get("META_PAGE_ACCESS_TOKEN")
page_id = os.environ.get("META_PAGE_ID")
if page_token and page_id:
    r2 = requests.get(
        f"{BASE_FB}/{page_id}",
        params={"fields": "name", "access_token": page_token},
        timeout=30,
    )
    print("FACEBOOK PAGE:", r2.status_code, r2.text)
    ok = ok and r2.ok
else:
    print("FACEBOOK PAGE: skipped (no token)")

print("META OK" if ok else "META FAILED")
