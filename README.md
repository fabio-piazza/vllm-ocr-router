# vllm-ocr-router

One RunPod pod, one GPU, one OpenAI-compatible port, two OCR models, no custom
image: the pod runs the stock `vllm/vllm-openai` image and its start command
fetches two files from this repository.

- `serve.sh` starts two `vllm serve` processes on local ports (the PDF model on
  8001, the image model on 8002) and the router on `$PORT`. If any of the three
  exits, the container exits so RunPod restarts it.
- `router.py` is a FastAPI forwarder: `POST /v1/chat/completions` goes to the
  vLLM that serves the request's `model`, body and `Authorization` header
  untouched, so each vLLM enforces `VLLM_API_KEY` itself. `GET /v1/models`
  merges both servers, `GET /health` is 200 only when both are up (503 while
  the models load).

## RunPod pod

- Image `vllm/vllm-openai:v0.32.0` (already cached on most RunPod hosts).
- Docker command (`bash -c`):

  ```bash
  curl -fsSL https://raw.githubusercontent.com/fabio-piazza/vllm-ocr-router/main/serve.sh | bash
  ```

  Set `ROUTER_REF` to a tag or commit to pin the version a pod runs.
- Expose `8080/tcp` (runpodProxy routes by pod name to private port 8080) and
  `22/tcp`.
- Volume of 20 GB on `/workspace`; both models together are under 10 GB.
- Env: `VLLM_API_KEY`, `HF_HOME=/workspace/hf_home`.
- An RTX 4090 holds both models with room for 16k-token contexts.

The OCR service (`ocr` repo) creates this pod with
`python benchmark/pods.py up ocr-router-prod` and checks it end to end with
`python benchmark/online_check.py ocr-router-prod`.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8080` | The port the router listens on (expose it on the pod) |
| `PDF_MODEL` | `SeerRay-Lab/Xiaomi-OCR-0` | Model for the PDF route |
| `IMAGE_MODEL` | `lightonai/LightOnOCR-3-0.8B` | Model for the image route |
| `PDF_MODEL_ARGS` | empty | Extra `vllm serve` flags for the PDF model |
| `IMAGE_MODEL_ARGS` | `--default-chat-template-kwargs {"enable_thinking":false}` | Extra flags for the image model |
| `GPU_FRACTION` | `0.42` | `--gpu-memory-utilization` of each server (two share the GPU) |
| `MAX_MODEL_LEN` | `16384` | `--max-model-len` of each server |
| `DOWNLOAD_DIR` | `/workspace/models` | Weights cache; put it on the pod volume |
| `ROUTER_REF` | `main` | Git ref of this repo the pod fetches `router.py` from |
| `VLLM_API_KEY` | unset | Bearer token both vLLM servers require |

## Tests

```bash
pip install -r requirements-test.txt
pytest -q
```
