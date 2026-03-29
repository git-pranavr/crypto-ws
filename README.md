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
