"""
Minimal AI Core Governance Proxy.

Demonstrates how to insert governance logic between consumers and the
AI Core orchestration endpoint:

  Consumer  --Bearer JWT-->  Proxy  --(provider URL passthrough)-->  AI Core

What this example does:
  - identifies the consumer from ext_attr.serviceinstanceid in their JWT
    (used for logging only here; the allowlist is global)
  - enforces a single global model allowlist on orchestration calls
  - logs token usage to stdout
  - passes everything else (admin, /v2/lm/...) straight through

What this example deliberately leaves out (production work):
  - per-consumer allowlists / token budgets backed by a database
  - rate limiting beyond a single proxy instance
  - streaming (SSE) -- non-trivial because tokens arrive in chunks
  - per-provider adapters for non-orchestration deployments
    (every provider's body schema is different)
  - content-safety policy injection (overriding the consumer's
    filtering_module_config to enforce mandatory filtering)
"""

import base64
import json
import os
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

AICORE_API_URL = os.environ["AICORE_API_URL"]

# Global allowlist. Common reason: vendor trust -- only OpenAI models are
# approved for this environment, Anthropic / Google / Meta require review.
ALLOWED_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-5"}

HOP_BY_HOP = {"host", "transfer-encoding", "connection", "content-length"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    yield
    await app.state.http.aclose()


app = FastAPI(title="AI Core Governance Proxy", lifespan=lifespan)


def consumer_id_from_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    parts = auth[7:].split(".")
    if len(parts) != 3:
        raise HTTPException(401, "Invalid token format")
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        raise HTTPException(401, "Cannot decode token")
    sid = payload.get("ext_attr", {}).get("serviceinstanceid")
    if not sid:
        raise HTTPException(401, "Token missing ext_attr.serviceinstanceid")
    return sid


def forward_headers(request: Request) -> dict:
    return {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v2/inference/deployments/{deployment_id}/completion")
async def orchestration_completion(deployment_id: str, request: Request):
    sid = consumer_id_from_token(request)
    body = await request.json()

    model = (
        body.get("orchestration_config", {})
        .get("module_configurations", {})
        .get("llm_module_config", {})
        .get("model_name")
    )

    if model not in ALLOWED_MODELS:
        return JSONResponse(
            status_code=403,
            content={
                "error": f"Model '{model}' not in allowlist",
                "allowed": sorted(ALLOWED_MODELS),
            },
        )

    upstream = f"{AICORE_API_URL}/v2/inference/deployments/{deployment_id}/completion"
    resp = await request.app.state.http.post(
        upstream, headers=forward_headers(request), json=body
    )

    if resp.status_code == 200:
        try:
            usage = resp.json().get("orchestration_result", {}).get("usage", {})
            print(
                f"usage consumer={sid} model={model} "
                f"tokens={usage.get('total_tokens', 0)}",
                flush=True,
            )
            # TODO: persist this to a database to enforce real budgets
        except json.JSONDecodeError:
            pass

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )


@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
)
async def passthrough(path: str, request: Request):
    """Forward every other AI Core call unchanged. The CaaS scopes on the
    consumer token already restrict what they can reach."""
    url = f"{AICORE_API_URL}/{path}"
    if request.url.query:
        url += f"?{request.url.query}"
    body = await request.body()
    resp = await request.app.state.http.request(
        request.method,
        url,
        headers=forward_headers(request),
        content=body or None,
    )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
