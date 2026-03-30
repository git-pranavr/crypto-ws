# Crypto Price Tracker

Small FastAPI service that listens to Binance ticker updates for `BTCUSDT`, `ETHUSDT`, and `BNBUSDT`, stores price changes in Postgres, and relays live updates to connected WebSocket clients.

Endpoints:
- `GET /health` returns service status
- `GET /price` returns the latest saved prices
- `WS /ws` streams live price updates

## Run

Create a `.env` file:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=crypto
PORT=8000
```

Run with Docker Compose:

```bash
docker compose up --build
```

The server will start on `http://localhost:8000` and run database migrations automatically on startup.

## Railway Deploy

This repo is set up for the simplest Railway layout:
- 1 app service built from the root `Dockerfile`
- 1 Railway PostgreSQL service

### Recommended setup

1. Deploy this repo as a new Railway service.
2. Add a PostgreSQL service to the same Railway project.
3. In the app service variables, set:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

If your database service is not named `Postgres`, replace the service name in the reference.

### Notes

- Railway will build from the checked-in `Dockerfile`.
- Railway injects `PORT` automatically, so you do not need to define it manually in the app service.
- The container starts with `entrypoint.sh`, retries migrations until the database is reachable, then starts Uvicorn on Railway's injected `PORT`.
- `railway.json` configures the Docker builder and uses `GET /health` for the service healthcheck.
- The market-data relay requires outbound WebSocket access to Binance. By default the app tries `wss://data-stream.binance.vision` first, then `wss://stream.binance.com:443`, and only uses `:9443` as a last fallback. If your platform enforces egress rules, whitelist those hosts on port `443`.

### Optional variables

```env
BINANCE_WS_BASE_URLS=wss://data-stream.binance.vision,wss://stream.binance.com:443,wss://stream.binance.com:9443
```

Use `BINANCE_WS_BASE_URLS` to override the upstream WebSocket endpoints or their order.
