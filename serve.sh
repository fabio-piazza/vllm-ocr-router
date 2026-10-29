#!/bin/bash
set -euo pipefail

: "${PORT:=8080}"
: "${PDF_MODEL:=SeerRay-Lab/Xiaomi-OCR-0}"
: "${IMAGE_MODEL:=lightonai/LightOnOCR-3-0.8B}"
DEFAULT_IMAGE_MODEL_ARGS='--default-chat-template-kwargs {"enable_thinking":false}'
: "${PDF_MODEL_ARGS:=}"
: "${IMAGE_MODEL_ARGS:=${DEFAULT_IMAGE_MODEL_ARGS}}"
: "${GPU_FRACTION:=0.42}"
: "${MAX_MODEL_LEN:=16384}"
: "${DOWNLOAD_DIR:=/workspace/models}"
: "${ROUTER_REF:=main}"
: "${ROUTER_DIR:=/opt/ocr}"

PDF_PORT=8001
IMAGE_PORT=8002
RAW_BASE="https://raw.githubusercontent.com/fabio-piazza/vllm-ocr-router/${ROUTER_REF}"
COMMON_ARGS="--host 127.0.0.1 --trust-remote-code \
    --download-dir ${DOWNLOAD_DIR} \
    --gpu-memory-utilization ${GPU_FRACTION} \
    --max-model-len ${MAX_MODEL_LEN}"

mkdir -p "${ROUTER_DIR}"
curl -fsSL "${RAW_BASE}/router.py" -o "${ROUTER_DIR}/router.py"

export OCR_ROUTES="{\"${PDF_MODEL}\": \"http://127.0.0.1:${PDF_PORT}\", \
\"${IMAGE_MODEL}\": \"http://127.0.0.1:${IMAGE_PORT}\"}"

echo "serving ${PDF_MODEL} (pdf) and ${IMAGE_MODEL} (image) on port ${PORT}"

vllm serve "${PDF_MODEL}" --port ${PDF_PORT} ${COMMON_ARGS} ${PDF_MODEL_ARGS} &
vllm serve "${IMAGE_MODEL}" --port ${IMAGE_PORT} ${COMMON_ARGS} ${IMAGE_MODEL_ARGS} &
python3 -m uvicorn router:app --app-dir "${ROUTER_DIR}" --host 0.0.0.0 --port "${PORT}" &

wait -n
echo "a server exited, stopping the pod so it restarts"
kill 0
exit 1
