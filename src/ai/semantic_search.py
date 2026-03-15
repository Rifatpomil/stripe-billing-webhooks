"""Semantic search over ledger entries using embeddings."""

from typing import Any

from src.config import get_settings


async def semantic_search_ledger(
    query: str,
    entries: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Rank ledger entries by semantic similarity to query.
    Uses OpenAI embeddings when available; falls back to keyword match.
    """
    settings = get_settings()
    if not settings.openai_api_key or not entries:
        return _keyword_fallback(query, entries, top_k)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        texts = [
            f"{e.get('event_type','')} {e.get('description','')} {e.get('stripe_customer_id','')} "
            f"amount={e.get('amount_cents',0)}"
            for e in entries
        ]
        embeds = await client.embeddings.create(
            model=settings.openai_embedding_model or "text-embedding-3-small",
            input=texts,
        )
        embed_list = [d.embedding for d in embeds.data]
        q_embeds = await client.embeddings.create(
            model=settings.openai_embedding_model or "text-embedding-3-small",
            input=[query],
        )
        q_embed = q_embeds.data[0].embedding

        def cos_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5
            nb = sum(y * y for y in b) ** 0.5
            return dot / (na * nb) if na and nb else 0

        scored = [(cos_sim(q_embed, emb), e) for emb, e in zip(embed_list, entries)]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]
    except Exception:
        return _keyword_fallback(query, entries, top_k)


def _keyword_fallback(
    query: str,
    entries: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    """Keyword-based ranking when embeddings unavailable."""
    q = query.lower()
    scored = []
    for e in entries:
        text = f"{e.get('event_type','')} {e.get('description','')} {e.get('stripe_customer_id','')}".lower()
        score = sum(1 for w in q.split() if w in text)
        scored.append((score, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]]
