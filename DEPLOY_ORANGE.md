# Step 1 — Deploy this smoke-test app to Orange cPanel

Goal: prove FastAPI (ASGI) can run under cPanel's "Setup Python App" (Passenger)
before any real astrology code gets ported over.

## 1. Local test first (optional but recommended)

```bash
cd webapp/astro-api
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Visit `http://127.0.0.1:8000/health` -> should return `{"status":"ok"}`.

## 2. cPanel: create the Python App

1. cPanel -> **Setup Python App** -> **Create Application**.
2. Python version: pick the newest available (3.10+).
3. Application root: e.g. `astro-api` (a folder under your home directory,
   separate from `public_html`).
4. Application URL: choose a subdomain, e.g. `astro-api.yourdomain.com`
   (create the subdomain first in cPanel -> Domains if it doesn't exist).
5. Application startup file: `passenger_wsgi.py`
6. Application Entry point: `application`
7. Click **Create**.

cPanel will show a command like:
```
source /home/<user>/virtualenv/astro-api/3.x/bin/activate && cd /home/<user>/astro-api
```

## 3. Upload the files

Upload `main.py`, `passenger_wsgi.py`, and `requirements.txt` into the
Application root folder shown above (File Manager or FTP).

## 4. Install dependencies via cPanel Terminal

Open cPanel -> **Terminal**, then run the `source ... && cd ...` command
cPanel gave you in step 2, followed by:

```bash
pip install -r requirements.txt
```

(Skip `uvicorn` for the live server — it's only used for local testing —
but installing it too is harmless.)

## 5. Restart the app

Back in **Setup Python App**, click **Restart**.

## 6. Verify

Visit:
- `https://astro-api.yourdomain.com/health` -> expect `{"status":"ok"}`
- POST `https://astro-api.yourdomain.com/echo` with JSON body
  `{"message": "hi"}` -> expect `{"received": "hi"}` (test with curl or
  Postman, since a browser can't POST directly)

```bash
curl -X POST https://astro-api.yourdomain.com/echo \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"hi\"}"
```

## If it fails

- Check **Setup Python App** page for a stderr/error log link.
- Common issue: `a2wsgi` not installed in the right virtualenv — make sure
  you ran the `source .../activate` command cPanel gave you *before*
  `pip install`.
- If Passenger's error log mentions ASGI/WSGI mismatch even with the
  shim, note the exact error — this is the specific risk this test step
  is meant to catch, and it may mean falling back to porting the
  astrology service as a plain Flask (WSGI-native) app instead of FastAPI.
