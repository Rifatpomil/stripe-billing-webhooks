"""AI-powered API endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.alerting import should_alert
from src.ai.anomaly_detection import detect_anomalies
from src.ai.churn_prediction import compute_churn_score
from src.ai.nl_query import answer_billing_query
from src.ai.observability import analyze_metric_trend
from src.ai.revenue_forecast import forecast_revenue
from src.ai.semantic_search import semantic_search_ledger
from src.ai.webhook_classifier import classify_webhook_event
from src.api.deps import get_db
from src.config import get_settings
from src.repositories.ledger_repository import LedgerRepository
from src.repositories.subscription_repository import SubscriptionRepository

router = APIRouter(prefix="/ai", tags=["ai"])


# --- Request/Response models ---
class AnomalyRequest(BaseModel):
    customer_id: str
    limit: int = 100


class NLQueryRequest(BaseModel):
    question: str
    customer_id: str | None = None


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ChurnRequest(BaseModel):
    customer_id: str


class ForecastRequest(BaseModel):
    customer_id: str
    horizon_days: int = 30


# --- Anomaly detection ---
@router.post("/anomaly/detect")
async def api_detect_anomaly(
    body: AnomalyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Detect anomalous billing patterns for a customer using Isolation Forest."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    repo = LedgerRepository(db)
    amounts = await repo.get_amounts_by_customer(body.customer_id, body.limit)
    result = detect_anomalies(amounts, threshold_std=settings.ai_anomaly_threshold_std)
    result["customer_id"] = body.customer_id
    return result


# --- Natural language query ---
@router.post("/query")
async def api_nl_query(
    body: NLQueryRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Answer natural language questions about billing (LLM when OPENAI_API_KEY set)."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    ledger_repo = LedgerRepository(db)
    context = {}
    if body.customer_id:
        amounts = await ledger_repo.get_amounts_by_customer(body.customer_id)
        context["amounts_by_customer"] = {body.customer_id: sum(amounts)}
        context["customer_ids"] = [body.customer_id]
    else:
        summary = await ledger_repo.get_aggregated_summary(limit=100)
        context["amounts_by_customer"] = summary
        context["customer_ids"] = list(summary.keys())
    return await answer_billing_query(body.question, context)


# --- Semantic search ---
@router.post("/search/ledger")
async def api_semantic_search(
    body: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Semantic search over ledger entries (embeddings when OPENAI_API_KEY set)."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    repo = LedgerRepository(db)
    entries = await repo.get_entries_recent(limit=50)
    entries_dict = [
        {
            "event_type": e.event_type,
            "stripe_customer_id": e.stripe_customer_id,
            "amount_cents": e.amount_cents,
            "description": e.description,
        }
        for e in entries
    ]
    results = await semantic_search_ledger(body.query, entries_dict, body.top_k)
    return {"query": body.query, "results": results}


# --- Churn prediction ---
@router.post("/churn/score")
async def api_churn_score(
    body: ChurnRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Compute churn risk score for a customer's subscriptions."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    sub_repo = SubscriptionRepository(db)
    ledger_repo = LedgerRepository(db)
    subs = await sub_repo.get_by_customer_id(body.customer_id)
    if not subs:
        return {"customer_id": body.customer_id, "churn_score": 0, "risk_tier": "low", "factors": []}
    sub = subs[0]
    amounts = await ledger_repo.get_amounts_by_customer(body.customer_id)
    sub_dict = {
        "status": sub.status,
        "cancel_at_period_end": sub.cancel_at_period_end,
    }
    result = compute_churn_score(sub_dict, amounts)
    result["customer_id"] = body.customer_id
    return result


# --- Revenue forecast ---
@router.post("/forecast/revenue")
async def api_revenue_forecast(
    body: ForecastRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Forecast revenue using historical ledger data (moving average)."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    repo = LedgerRepository(db)
    historical = await repo.get_historical_amounts_for_forecast(body.customer_id, limit=90)
    result = forecast_revenue(historical, body.horizon_days)
    result["customer_id"] = body.customer_id
    return result


# --- Webhook classifier ---
@router.post("/classify/webhook")
async def api_classify_webhook(
    event_type: str = Query(...),
) -> dict:
    """Classify webhook event type with suggested handling (rule-based + optional LLM)."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    return classify_webhook_event(event_type)


# --- Alert evaluation ---
@router.get("/alert/evaluate")
async def api_alert_evaluate(
    metric: str = Query(...),
    value: float = Query(...),
    baseline_mean: float = Query(...),
    baseline_std: float = Query(0.1),
) -> dict:
    """Evaluate if a metric value warrants an alert (statistical outlier)."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    return should_alert(metric, value, baseline_mean, baseline_std)


# --- Conversational admin ---
class AdminChatRequest(BaseModel):
    message: str


@router.post("/admin/chat")
async def api_admin_chat(
    body: AdminChatRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Chat with the system about billing state (LLM when OPENAI_API_KEY set)."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    ledger_repo = LedgerRepository(db)
    sub_repo = SubscriptionRepository(db)
    summary = await ledger_repo.get_aggregated_summary(limit=20)
    context = {"ledger_summary": summary, "customer_count": len(summary)}
    if settings.openai_api_key:
        result = await answer_billing_query(
            f"System state: {context}. User asks: {body.message}", context
        )
        return {"response": result["answer"], "source": result.get("source", "llm")}
    return {
        "response": f"Ledger has {context['customer_count']} customers. Configure OPENAI_API_KEY for detailed chat.",
        "source": "template",
    }


# --- Metric trend analysis ---
@router.get("/observability/trend")
async def api_metric_trend(
    values: str = Query(..., description="Comma-separated float values"),
    window: int = Query(5, ge=2),
) -> dict:
    """Analyze metric trend and detect anomalies in a time series."""
    settings = get_settings()
    if not settings.ai_features_enabled:
        return {"enabled": False, "message": "AI features disabled"}
    vals = [float(x.strip()) for x in values.split(",") if x.strip()]
    return analyze_metric_trend(vals, window)
