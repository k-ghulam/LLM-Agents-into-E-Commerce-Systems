# KooshkWear public demo on Render

Prepared service configuration (not yet deployed):

| Setting | Value |
| --- | --- |
| Repository | https://github.com/k-ghulam/LLM-Agents-into-E-Commerce-Systems |
| Branch | main, after the EUR update is pushed |
| Runtime | Docker |
| Dockerfile | ./Dockerfile |
| Context | . |
| Plan | Free |
| Region | Frankfurt |
| Health path | /health |
| Start command | Dockerfile default, binds 0.0.0.0:$PORT |

One web service serves the frontend and API; Atlas remains the external database. No local MongoDB container or Docker Desktop is needed on the user's computer. Confirm the Render workspace before creating the service.

1. Apply the update, run the offline checks below, commit the changed files and push main.
2. Create the Docker web service from the existing repository, on the Free plan.
3. In Render **Environment**, privately add `MONGO_URI` from your local configuration and `GROQ_API_KEY` if chat is needed. Never commit `.env`. Set `ONLINE_EVALS_ENABLED=false`. The existing database is `ecommerce_db`; use a dedicated demo database/account and sample data rather than real customer information. Only grant application-level database permissions.
4. From the service's **Connect > Outbound** details, add its outbound IP ranges to Atlas Network Access. Keep access restricted to the hosting ranges and your development IP.
5. Save environment changes and deploy. Database access must work before application startup can finish. A missing URI falls back to localhost and will fail on Render.
6. If using Google login, add the final HTTPS origin to the Google client configuration and set `GOOGLE_CLIENT_ID` in Render. Password sign-in does not require Google configuration.
7. Wait for Render status **Live**. Record the actual URL shown in the Dashboard, then check `/health`, `/`, `/products` and a decimal price filter. Confirm the expected KooshkWear branding, sign in with a test account, and verify a EUR 19.99 product at quantity 3 records EUR 59.97. Test one allowed shopping query and an empty search, and check logs for errors. Only then describe the URL as verified.

Free services sleep after inactivity and the next request can be slow. See https://render.com/docs/free. Free hosting is suitable for a demo; this change does not complete the production release work in README.md.

## Offline checks

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q backend main.py
python -m pip check
node scripts/check-frontend.mjs
node scripts/check-money.mjs
```

Node is only required for development checks. Runtime is Python 3.12 and does not need a frontend build. No deployment, hosted database connection, live provider response or browser session was exercised by these offline checks. A live URL is pending GitHub push, workspace confirmation and private environment configuration.
