#!/bin/bash
set -euo pipefail

PDF_PORT=8001
IMAGE_PORT=8002
IMAGE_MODEL_ARGS="${IMAGE_MODEL_ARGS:---default-chat-template-kwargs {\"enable_thinking\":false}}"
PDF_MODEL_ARGS="${PDF_MODEL_ARGS:-}"
COMMON_ARGS="--host 127.0.0.1 --trust-remote-code \
    --download-dir ${DOWNLOAD_DIR} \
    --gpu-memory-utilization ${GPU_FRACTION} \
    --max-model-len ${MAX_MODEL_LEN}"

export OCR_ROUTES="{\"${PDF_MODEL}\": \"http://127.0.0.1:${PDF_PORT}\", \
\"${IMAGE_MODEL}\": \"http://127.0.0.1:${IMAGE_PORT}\"}"

echo "serving ${PDF_MODEL} (pdf) and ${IMAGE_MODEL} (image) on port ${PORT}"

vllm serve "${PDF_MODEL}" --port ${PDF_PORT} ${COMMON_ARGS} ${PDF_MODEL_ARGS} &
vllm serve "${IMAGE_MODEL}" --port ${IMAGE_PORT} ${COMMON_ARGS} ${IMAGE_MODEL_ARGS} &
python3 -m uvicorn router:app --app-dir /opt/ocr --host 0.0.0.0 --port "${PORT}" &

wait -n
echo "a server exited, stopping the pod so it restarts"
kill 0
exit 1
