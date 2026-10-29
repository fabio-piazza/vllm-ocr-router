import json
import os

import httpx
from fastapi import FastAPI, Request, Response

ROUTES = json.loads(os.environ["OCR_ROUTES"])
UPSTREAM_TIMEOUT_SECONDS = 600.0
JSON_MEDIA_TYPE = "application/json"
MODELS_PATH = "/v1/models"
CHAT_PATH = "/v1/chat/completions"
HEALTH_PATH = "/health"
STATUS_OK = 200
STATUS_NOT_FOUND = 404
STATUS_UNAVAILABLE = 503
UNKNOWN_MODEL_MESSAGE = "unknown model {model!r}; served: {served}"
UNREACHABLE_MESSAGE = "upstream for {model!r} is not reachable yet"

app = FastAPI()
client = httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS)


@app.get(HEALTH_PATH)
async def health() -> Response:
    for base in ROUTES.values():
        if not await _is_healthy(base):
            return Response(status_code=STATUS_UNAVAILABLE)
    return Response(status_code=STATUS_OK)


@app.get(MODELS_PATH)
async def models(request: Request) -> Response:
    served = []
    for base in ROUTES.values():
        served += await _models_of(base, request)
    body = {"object": "list", "data": served}
    return _json_response(body, STATUS_OK)


@app.post(CHAT_PATH)
async def chat(request: Request) -> Response:
    body = await request.body()
    model = json.loads(body).get("model")
    base = ROUTES.get(model)
    if base is None:
        served = sorted(ROUTES)
        message = UNKNOWN_MODEL_MESSAGE.format(model=model, served=served)
        return _error_response(message, STATUS_NOT_FOUND)
    headers = _upstream_headers(request)
    upstream = base + CHAT_PATH
    try:
        reply = await client.post(upstream, content=body, headers=headers)
    except httpx.TransportError:
        message = UNREACHABLE_MESSAGE.format(model=model)
        return _error_response(message, STATUS_UNAVAILABLE)
    return Response(
        content=reply.content,
        status_code=reply.status_code,
        media_type=JSON_MEDIA_TYPE,
    )


async def _is_healthy(base: str) -> bool:
    try:
        reply = await client.get(base + HEALTH_PATH)
    except httpx.TransportError:
        return False
    return reply.status_code == STATUS_OK


async def _models_of(base: str, request: Request) -> list:
    headers = _upstream_headers(request)
    try:
        reply = await client.get(base + MODELS_PATH, headers=headers)
    except httpx.TransportError:
        return []
    if reply.status_code != STATUS_OK:
        return []
    return reply.json()["data"]


def _upstream_headers(request: Request) -> dict:
    authorization = request.headers.get("authorization", "")
    return {"content-type": JSON_MEDIA_TYPE, "authorization": authorization}


def _error_response(message: str, status: int) -> Response:
    return _json_response({"error": message}, status)


def _json_response(body: dict, status: int) -> Response:
    content = json.dumps(body)
    return Response(
        content=content, status_code=status, media_type=JSON_MEDIA_TYPE,
    )
