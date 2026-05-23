"""Quick test: is IRAS PSC available via IRSA TAP?"""
import urllib.request, urllib.parse, ssl, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://irsa.ipac.caltech.edu/TAP/sync"
HEADERS = {"Accept": "application/x-votable+xml"}

sql = "SELECT TOP 3 ra, dec, f12, f25 FROM iras.psc"
params = urllib.parse.urlencode({"query": sql})
url = f"{BASE}?{params}"

req = urllib.request.Request(url, headers=HEADERS)
try:
    resp = urllib.request.urlopen(req, timeout=30, context=ctx)
    text = resp.read().decode("utf-8")
    if "TABLE" in text and "FIELD" in text:
        print("IRAS PSC: OK (TAP accessible)")
    elif "ERROR" in text.upper():
        print(f"IRAS PSC: FAIL (TAP error)")
    else:
        print("IRAS PSC: ? (unexpected response)")
except Exception as e:
    print(f"IRAS PSC: FAIL ({e})")
    sys.exit(1)
