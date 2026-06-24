PRICE_PER_MILLION_TOKENS = {
    # OpenAI published standard rates checked 2026-06-24. Cached-input discounts are
    # intentionally ignored, so this is a conservative estimate rather than a bill.
    "gpt-4.1-mini": (0.40, 1.60),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    rates = PRICE_PER_MILLION_TOKENS.get(model)
    if rates is None:
        return None
    input_rate, output_rate = rates
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
