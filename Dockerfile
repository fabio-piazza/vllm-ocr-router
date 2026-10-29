FROM vllm/vllm-openai:v0.32.0

COPY --chmod=755 serve.sh /opt/ocr/serve.sh
COPY router.py /opt/ocr/router.py

ENV PORT=8080 \
    PDF_MODEL=SeerRay-Lab/Xiaomi-OCR-0 \
    IMAGE_MODEL=lightonai/LightOnOCR-3-0.8B \
    GPU_FRACTION=0.42 \
    MAX_MODEL_LEN=16384 \
    DOWNLOAD_DIR=/workspace/models

ENTRYPOINT ["/opt/ocr/serve.sh"]
