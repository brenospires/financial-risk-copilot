def normalize_ticker(ticker: str) -> str:
    """Return a normalized ticker suitable for internal matching."""

    normalized_ticker = ticker.upper().strip().replace("$", "")

    if not normalized_ticker:
        raise ValueError("ticker cannot be empty")

    return normalized_ticker
