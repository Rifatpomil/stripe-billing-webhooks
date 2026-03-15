# Billing Webhooks Service

Stripe webhook processing service with subscription state machine, append-only ledger, idempotency, and metered billing support.

## Features

- **P0**: Webhook signature verification, idempotency, subscription state machine, append-only ledger
- **P1**: Retry queue for failed webhooks, DLQ, admin reprocess endpoint, background retry worker
- **P2**: Metered billing usage table and aggregation
- **Observability**: Structured logging (structlog), Prometheus metrics, custom error responses
- **AI/ML**: Anomaly detection, NL query, churn prediction, revenue forecast, semantic search, conversational admin

## Quick Start

```bash
# Start Postgres + app
docker-compose up -d

# Run migrations (if not auto-run)
docker-compose exec app alembic upgrade head
```

**Dashboard UI**: Open http://localhost:8000 for the billing dashboard (subscriptions, usage, AI insights, admin).

## API Endpoints

### Webhooks

```bash
# Stripe webhook (requires valid Stripe-Signature header)
curl -X POST http://localhost:8000/v1/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=...,v1=..." \
  -d '{"id":"evt_123","type":"customer.subscription.created","data":{"object":{...}}}'
```

### Subscriptions

```bash
# Get subscriptions for a customer
curl http://localhost:8000/v1/subscriptions/cus_xxx
```

### Checkout (optional)

```bash
# Create checkout session
curl -X POST http://localhost:8000/v1/checkout/session \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cus_xxx",
    "price_id": "price_xxx",
    "success_url": "https://example.com/success",
    "cancel_url": "https://example.com/cancel"
  }'
```

### Admin

```bash
# Reprocess a failed event
curl -X POST http://localhost:8000/v1/admin/reprocess/evt_xxx
```

### Usage (P2)

```bash
# Create usage record
curl -X POST http://localhost:8000/v1/usage/records \
  -H "Content-Type: application/json" \
  -d '{
    "stripe_customer_id": "cus_xxx",
    "stripe_subscription_item_id": "si_xxx",
    "meter_name": "api_calls",
    "quantity": 10
  }'

# Get aggregated usage
curl "http://localhost:8000/v1/usage/aggregate/cus_xxx?meter_name=api_calls&days=30"
```

### AI Endpoints

```bash
# Anomaly detection (Isolation Forest)
curl -X POST http://localhost:8000/v1/ai/anomaly/detect \
  -H "Content-Type: application/json" -d '{"customer_id":"cus_xxx"}'

# Natural language billing query (LLM when OPENAI_API_KEY set)
curl -X POST http://localhost:8000/v1/ai/query \
  -H "Content-Type: application/json" -d '{"question":"What is total revenue?","customer_id":"cus_xxx"}'

# Churn risk score
curl -X POST http://localhost:8000/v1/ai/churn/score \
  -H "Content-Type: application/json" -d '{"customer_id":"cus_xxx"}'

# Revenue forecast
curl -X POST http://localhost:8000/v1/ai/forecast/revenue \
  -H "Content-Type: application/json" -d '{"customer_id":"cus_xxx","horizon_days":30}'

# Semantic search over ledger (embeddings when OPENAI_API_KEY set)
curl -X POST http://localhost:8000/v1/ai/search/ledger \
  -H "Content-Type: application/json" -d '{"query":"failed payments","top_k":5}'

# Conversational admin
curl -X POST http://localhost:8000/v1/ai/admin/chat \
  -H "Content-Type: application/json" -d '{"message":"How many failed events?"}'
```

Set `OPENAI_API_KEY` for LLM and embeddings. Set `AI_FEATURES_ENABLED=false` to disable.

## Local Development

```bash
# Create venv and install
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"

# Start Postgres
docker-compose up -d postgres

# Set env (copy .env.example to .env)
cp .env.example .env

# Run migrations
alembic upgrade head

# Run app
uvicorn src.main:app --reload

# Run tests
pytest

# Run tests with Postgres (for trigger tests)
$env:TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/billing_test"; pytest
```

## Observability

- **Logging**: Structured JSON logs (structlog). Set `DEBUG=1` for console output.
- **Metrics**: Prometheus metrics at `GET /metrics` (request count, latency, webhook stats).
- **Health**: `GET /health` for liveness.

## Stripe Webhook Testing

Use [Stripe CLI](https://stripe.com/docs/stripe-cli) to forward webhooks:

```bash
stripe listen --forward-to localhost:8000/v1/webhooks/stripe
# Copy the webhook signing secret (whsec_...) to .env
```

## Database Schema

- **webhook_events**: Append-only raw events, idempotency by `event_id`
- **subscriptions**: State machine with DB trigger enforcing valid transitions
- **ledger_entries**: Append-only billing ledger
- **webhook_retry_queue**: Failed events for retry
- **webhook_dlq**: Dead letter queue
- **usage_records**: Metered billing sample data

## Valid Subscription Transitions

| From       | To                    |
|-----------|------------------------|
| incomplete | active, canceled, incomplete_expired |
| trialing  | active, canceled, past_due |
| active    | past_due, canceled, trialing |
| past_due  | active, canceled, unpaid |
| unpaid    | canceled, active      |

## License

MIT
