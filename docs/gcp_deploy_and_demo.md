# GCP Deploy And Demo Runbook

## Branch

Use `feature/integrated-backend` as the integrated backend branch. It is based on `demo/local-full` and includes the frontend-facing routers:

- `/auth`
- `/users`
- `/prices`
- `/recommendation`
- `/basket`
- `/trade`
- `/ai`
- `/market`
- KIS price/chart endpoints from `app/routes_kis.py`

## GCP VM Deployment

Recommended first VM size for a presentation/demo is `e2-standard-2` with a 100 GB standard persistent disk. Use `e2-standard-4` if ClickHouse, reports, and backtest traffic all run at once.

1. Create a VM and install Docker + Docker Compose plugin.
2. Clone this repository and check out `feature/integrated-backend`.
3. Copy `.env.gcp.example` to `.env.gcp`.
4. Replace every `CHANGE_ME_*`, `YOUR_FRONTEND_DOMAIN`, and `YOUR_BACKEND_DOMAIN` value.
5. Keep `KIS_MOCK=true` and `KIS_REAL_TRADING_ENABLED=false` unless real trading is explicitly approved.
6. Start the stack:

```bash
docker compose --env-file .env.gcp -f docker-compose.gcp.yml up -d --build
```

7. Check health:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/
```

8. Open only the ports needed for the presentation. Usually expose `8000` through a reverse proxy or load balancer, not every database port.

## If GCP Cannot Be Started

Use the local integrated demo mode and record the full flow.

1. Copy `.env.example` to `.env`.
2. Keep:

```env
DEMO_MODE=true
AI_ALLOW_DUMMY_PREDICTIONS=true
KIS_MOCK=true
KIS_REAL_TRADING_ENABLED=false
```

3. If Docker is unavailable, use SQLite in `.env`:

```env
DATABASE_URL=sqlite:///./local_demo.db
MARKET_DB_URL=sqlite:///./local_market_demo.db
```

4. Run the backend with the existing API environment, not the base conda Python:

```bash
/home/jeongeun/miniconda3/envs/api_env/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. Run the frontend with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
6. Record these scenes:

- Login or demo-authenticated page load.
- Market ranking and KIS chart/current-price screen.
- Recommendation report generation or saved report display.
- Basket/watchlist flow.
- Trade/autotrade screen with mock KIS and dummy AI prediction labels.
- Backtest request and result screen.
- Final architecture slide: frontend, backend, KIS, AI server webhook, app DB, market DB, ClickHouse.

For the recording, say clearly that live credentials and real trading are disabled for safety, while the same API paths are used for GCP deployment.
