"""Natural language query over billing data using LLM."""

import json
from typing import Any

from src.config import get_settings


async def answer_billing_query(
    question: str,
    context_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Use LLM to answer natural language questions about billing data.
    Requires OPENAI_API_KEY. Falls back to template responses when not configured.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return _template_response(question, context_data)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        context_str = json.dumps(context_data, indent=2)
        response = await client.chat.completions.create(
            model=settings.openai_model or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a billing analyst. Answer questions about billing data concisely. "
                        "Use only the provided context. If the context lacks information, say so."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context_str}\n\nQuestion: {question}",
                },
            ],
            max_tokens=500,
        )
        answer = response.choices[0].message.content or ""
        return {"answer": answer, "model": settings.openai_model, "source": "llm"}
    except Exception:
        return _template_response(question, context_data)


def _template_response(question: str, context: dict[str, Any]) -> dict[str, Any]:
    """Fallback when LLM not available: simple keyword-based response."""
    q = question.lower()
    if "total" in q or "revenue" in q or "sum" in q:
        total = sum(
            a for a in context.get("amounts_by_customer", {}).values() if isinstance(a, (int, float))
        )
        return {
            "answer": f"Total revenue from ledger: {total} cents.",
            "source": "template",
        }
    if "customer" in q:
        customers = context.get("customer_ids", []) or list(
            context.get("amounts_by_customer", {}).keys()
        )
        return {"answer": f"Customers in context: {len(customers)}", "source": "template"}
    return {
        "answer": "I can answer questions about totals, customers, and revenue. Please configure OPENAI_API_KEY for detailed answers.",
        "source": "template",
    }
