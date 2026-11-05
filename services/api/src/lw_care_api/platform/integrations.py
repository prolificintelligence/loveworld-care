"""Real provider probes and a shared AI control; no patient data leaves this module."""

import httpx

from .domain import RuleError, require

AI_DISABLED_KEY = "lwh:platform:ai-disabled"


async def redis_command(cfg, command):
    require(
        cfg.upstash_rest_url and cfg.upstash_rest_token,
        "AUTHORITY_UNAVAILABLE",
        "The shared integration control store is not configured",
        503,
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                cfg.upstash_rest_url,
                headers={
                    "Authorization": "Bearer " + cfg.upstash_rest_token,
                },
                json=command,
            )
        require(
            response.is_success,
            "AUTHORITY_UNAVAILABLE",
            "The shared integration control store is unavailable",
            503,
        )
        data = response.json()
        require(
            "error" not in data and "result" in data,
            "AUTHORITY_UNAVAILABLE",
            "The shared integration control store rejected the operation",
            503,
        )
        return data["result"]
    except (httpx.HTTPError, ValueError) as exc:
        raise RuleError(
            "AUTHORITY_UNAVAILABLE", "The shared integration control store is unavailable", 503
        ) from exc


async def verify_free_model(cfg):
    require(
        cfg.openrouter_api_key and cfg.openrouter_model.endswith(":free"),
        "AUTHORITY_UNAVAILABLE",
        "A free model and its provider credential must be configured",
        503,
    )
    disabled = await redis_command(cfg, ["GET", AI_DISABLED_KEY])
    require(
        disabled == "0",
        "POLICY_NOT_ACTIVE",
        "AI verification is disabled by the shared control",
        409,
    )
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer " + cfg.openrouter_api_key,
                },
                json={
                    "model": cfg.openrouter_model,
                    "messages": [{"role": "user", "content": "Reply with the single word READY."}],
                    "max_tokens": 512,
                    "reasoning": {"enabled": False},
                    "provider": {"max_price": {"prompt": 0, "completion": 0}},
                },
            )
        if response.status_code == 429:
            raise RuleError(
                "RATE_LIMITED",
                "The free model is rate limited. Retry later; no paid fallback was used.",
                429,
            )
        require(
            response.is_success,
            "AUTHORITY_UNAVAILABLE",
            "The free model provider could not complete verification",
            503,
        )
        data = response.json()
        choices = data.get("choices", [])
        content = choices[0].get("message", {}).get("content") if choices else None
        require(
            isinstance(content, str) and bool(content.strip()),
            "AUTHORITY_UNAVAILABLE",
            "The free model did not return a usable verification response",
            503,
        )
        return {
            "status": "PROVIDER_COMPLETED",
            "model": data.get("model"),
            "provider_request_id": data.get("id"),
            "cost": data.get("usage", {}).get("cost"),
            "probe": "FIXED_PUBLIC_READINESS_TEXT",
            "patient_data_transmitted": False,
        }
    except (httpx.HTTPError, ValueError) as exc:
        raise RuleError(
            "AUTHORITY_UNAVAILABLE", "The free model provider is unavailable", 503
        ) from exc
