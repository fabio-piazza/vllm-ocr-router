import json
import os

import httpx
import pytest
from fastapi.testclient import TestClient

PDF_MODEL = "pdf/model"
IMAGE_MODEL = "image/model"
PDF_BASE = "http://pdf:8001"
IMAGE_BASE = "http://image:8002"
BEARER = "Bearer secret"
COMPLETION = {"choices": [{"message": {"content": "page text"}}]}

os.environ["OCR_ROUTES"] = json.dumps({
    PDF_MODEL: PDF_BASE,
    IMAGE_MODEL: IMAGE_BASE,
})

import router


class FakeUpstreams:

    def __init__(self):
        self.calls = []
        self.down = set()

    def handle(self, request: httpx.Request) -> httpx.Response:
        base = f"{request.url.scheme}://{request.url.netloc.decode()}"
        self.calls.append((base, request.url.path, request.headers, request.content))
        if base in self.down:
            raise httpx.ConnectError("refused")
        if request.url.path == "/health":
            return httpx.Response(200)
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": base}]})
        return httpx.Response(200, json=COMPLETION)


@pytest.fixture
def upstreams(monkeypatch):
    fake = FakeUpstreams()
    transport = httpx.MockTransport(fake.handle)
    monkeypatch.setattr(router, "client", httpx.AsyncClient(transport=transport))
    return fake


@pytest.fixture
def api(upstreams):
    return TestClient(router.app)


@pytest.fixture
def pdf_reply(api):
    body = {"model": PDF_MODEL, "messages": []}
    return api.post("/v1/chat/completions", json=body, headers={"Authorization": BEARER})


def test_health_is_ok_when_both_upstreams_answer(api):
    assert api.get("/health").status_code == 200


def test_health_is_unavailable_while_one_upstream_is_down(api, upstreams):
    upstreams.down.add(IMAGE_BASE)

    assert api.get("/health").status_code == 503


def test_models_merges_both_upstreams(api):
    ids = [m["id"] for m in api.get("/v1/models").json()["data"]]

    assert ids == [PDF_BASE, IMAGE_BASE]


def test_models_skips_an_upstream_that_is_down(api, upstreams):
    upstreams.down.add(PDF_BASE)

    assert api.get("/v1/models").json()["data"] == [{"id": IMAGE_BASE}]


def test_chat_goes_to_the_upstream_of_the_model(pdf_reply, upstreams):
    assert upstreams.calls[-1][:2] == (PDF_BASE, "/v1/chat/completions")


def test_chat_forwards_the_body_untouched(pdf_reply, upstreams):
    assert json.loads(upstreams.calls[-1][3]) == {"model": PDF_MODEL, "messages": []}


def test_chat_forwards_the_bearer_token(pdf_reply, upstreams):
    assert upstreams.calls[-1][2]["authorization"] == BEARER


def test_chat_returns_the_upstream_completion(pdf_reply):
    assert pdf_reply.json() == COMPLETION


def test_chat_rejects_an_unknown_model(api):
    reply = api.post("/v1/chat/completions", json={"model": "other"})

    assert reply.status_code == 404


def test_chat_is_unavailable_while_the_upstream_is_down(api, upstreams):
    upstreams.down.add(IMAGE_BASE)

    reply = api.post("/v1/chat/completions", json={"model": IMAGE_MODEL})

    assert reply.status_code == 503
