# Local AI Inference Runbook

## Current wiring

- Backend app DB: `DATABASE_URL`, default `postgresql://trader:traderpass@localhost:5432/trading`
- Backend market DB: `MARKET_DB_URL`, default `postgresql://trader:traderpass@localhost:5433/market_data`
- AI inference DB: `stock_db` on local port `5435`, added as `ai-stock-db` in `docker-compose.yml`
- AI command flow: backend queues `START`, `STOP`, `ONCE` under `/ai/commands/*`; AI `poll_commands.py` polls them.
- AI result flow: AI posts 5-minute results to `/ai/realtime`; ONCE report results to `/ai/callback`.

## Files still needed from the AI side

The workspace currently does not contain these required runtime artifacts:

- `stock_db.dump`
- TFT model state dict, for example `best_model_state_dict.pt`
- A Python environment with packages used by `Gentle_Viking_AI_inference/inference_code`

## Restore the AI DB

Start the AI DB service:

```bash
docker compose up -d ai-stock-db
```

Restore the dump after placing `stock_db.dump` somewhere local:

```bash
pg_restore -h localhost -p 5435 -U stock_user -d stock_db -v /path/to/stock_db.dump
```

Use this DB configuration when running AI scripts:

```bash
export DB_HOST=localhost
export DB_PORT=5435
export DB_NAME=stock_db
export DB_USER=stock_user
export DB_PASSWORD=stockpass
```

## Backend environment

Use the same AI API key on both sides:

```bash
export AI_SERVER_API_KEY=dev-ai-key
```

For KIS mock trading:

```bash
export KIS_MOCK=true
export KIS_APP_KEY=...
export KIS_APP_SECRET=...
export KIS_ACC_NO=...
```

For KIS real account credentials, switch the host URLs by setting mock false. Real orders are still blocked unless explicitly enabled:

```bash
export KIS_MOCK=false
export KIS_APP_KEY=...
export KIS_APP_SECRET=...
export KIS_ACC_NO=...
export KIS_REAL_TRADING_ENABLED=false
```

Only set `KIS_REAL_TRADING_ENABLED=true` when you intentionally want the backend to submit live orders.

## AI script environment

The copied AI scripts currently use `/home/user` paths for `active_tickers.json`, script base path, and the default model path. Either run them from a matching path/symlink or patch those constants before production use. Minimum environment:

```bash
export BACKEND_WEBHOOK_URL=http://localhost:8000
export AI_SERVER_API_KEY=dev-ai-key
export TFT_MODEL_PATH=/path/to/best_model_state_dict.pt
```

Then run command polling:

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
python poll_commands.py
```

For 5-minute inference push during market hours, run `inference_pipeline.py` on a schedule after fixing its hardcoded `BASE` and `PYTHON` paths.

## What works after artifacts are present

- Recommendation report: frontend/backend queues ONCE, AI callbacks to `/ai/callback`, backend generates and stores the report.
- Probability result: AI posts probabilities to `/ai/realtime`, backend exposes `/ai/predictions` and `/ai/predictions/{ticker}`.
- Auto trading: `/trade/start` queues START and waits for pushed AI signals. If no AI signal exists, backend now returns HOLD with confidence 0 instead of random BUY/SELL.

## Exact Local Run Commands

Run these from the backend repository unless the command says otherwise.

### 1. Start databases

```bash
cd /home/jeongeun/capstone2/Back-Gentle-Viking
docker compose up -d app-db market-db ai-stock-db redis
```

### 2. Restore the AI DB dump

```bash
cd /home/jeongeun/capstone2/Back-Gentle-Viking
PGPASSWORD=stockpass pg_restore -h localhost -p 5435 -U stock_user -d stock_db -v local_ai_artifacts/stock_db.dump
```

If the DB already has restored tables and `pg_restore` complains about existing objects, recreate only the AI DB volume/container before restoring. Do not do this if you need to keep existing AI DB changes.

### 3. Start backend

```bash
cd /home/jeongeun/capstone2/Back-Gentle-Viking
/home/jeongeun/miniconda3/envs/api_env/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend communication endpoints:

```text
POST http://localhost:8000/ai/commands/push
GET  http://localhost:8000/ai/commands/pending
POST http://localhost:8000/ai/realtime
POST http://localhost:8000/ai/callback
GET  http://localhost:8000/ai/predictions
GET  http://localhost:8000/ai/predictions/{ticker}
```

### 4. Start AI command polling

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
python poll_commands.py
```

For a one-shot polling test:

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
python poll_commands.py --once
```

### 5. Queue a START command manually

```bash
curl -X POST http://localhost:8000/ai/commands/push \
  -H "Content-Type: application/json" \
  -d '{"command":"START","user_id":1,"tickers":["005930","000660"]}'
```

Check that AI registered the tickers:

```bash
cat /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code/active_tickers.json
```

### 6. Run one 5-minute inference push manually

`inference_pipeline.py` has market-hours guards. During market hours, run:

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
python inference_pipeline.py
```

If inference results already exist in `inference_results`, you can test only the backend push step:

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
python push_realtime_results.py
curl http://localhost:8000/ai/predictions
```

### 7. Queue an ONCE report command manually

```bash
curl -X POST http://localhost:8000/ai/commands/push \
  -H "Content-Type: application/json" \
  -d '{"command":"ONCE","user_id":1,"tickers":["005930","000660"],"callback_url":"http://localhost:8000/ai/callback"}'
```

Then poll once or keep the poller running:

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
python poll_commands.py --once
```

Check callback result through the returned/generated job id if you used the app flow. Manual command without `job_id` generates a report id in the AI log.

## Final Demo Startup Commands

Open separate terminals for backend, AI, and frontend.

### Terminal 1 - databases

```bash
cd /home/jeongeun/capstone2/Back-Gentle-Viking
docker compose up -d app-db market-db ai-stock-db redis
```

Restore the AI dump once, or only when you recreated `ai-stock-db`:

```bash
cd /home/jeongeun/capstone2/Back-Gentle-Viking
PGPASSWORD=stockpass pg_restore -h localhost -p 5435 -U stock_user -d stock_db -v local_ai_artifacts/stock_db.dump
```

### Terminal 2 - backend

```bash
cd /home/jeongeun/capstone2/Back-Gentle-Viking
/home/jeongeun/miniconda3/envs/api_env/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 3 - AI command poller

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
conda run -n tft_env python poll_commands.py
```

### Terminal 4 - optional AI 5-minute inference push

During market hours, run the full pipeline:

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
conda run -n tft_env python inference_pipeline.py
```

If `inference_results` already has rows and you only want to push them to backend:

```bash
cd /home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code
conda run -n tft_env python push_realtime_results.py
```

### Terminal 5 - frontend

```bash
cd /home/jeongeun/capstone2/Front-Gentle-Viking
npm run dev
```

Frontend URL: `http://localhost:3000` or the port printed by Next.js.
Backend URL: `http://localhost:8000`.

### Manual connection checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ai/predictions
curl -X POST http://localhost:8000/ai/commands/push \
  -H "Content-Type: application/json" \
  -d '{"command":"START","user_id":1,"tickers":["005930","000660"]}'
```

Then watch Terminal 3. The poller should log the START command and update:

```text
/home/jeongeun/capstone2/AI-Gentle-VIking/Gentle_Viking_AI_inference/inference_code/active_tickers.json
```
