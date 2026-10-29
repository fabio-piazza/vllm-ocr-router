import os
import subprocess
from pathlib import Path

import pytest

SERVE_SCRIPT = Path(__file__).resolve().parent.parent / "serve.sh"
FAKE_VLLM = '#!/bin/bash\nprintf "%s\\n" "$@" >> "$ARGS_LOG"\n'
FAKE_CURL = '#!/bin/bash\ntouch "$4"\n'
FAKE_PYTHON = "#!/bin/bash\n"
CHAT_TEMPLATE_KWARGS = '{"enable_thinking":false}'
TIMEOUT_SECONDS = 10


def _install_fake(bin_dir: Path, name: str, body: str) -> None:
    fake = bin_dir / name
    fake.write_text(body)
    fake.chmod(0o755)


@pytest.fixture
def served_args(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _install_fake(bin_dir, "vllm", FAKE_VLLM)
    _install_fake(bin_dir, "curl", FAKE_CURL)
    _install_fake(bin_dir, "python3", FAKE_PYTHON)
    args_log = tmp_path / "args.log"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "ARGS_LOG": str(args_log),
        "ROUTER_DIR": str(tmp_path / "router"),
    }
    subprocess.run(
        ["bash", str(SERVE_SCRIPT)],
        env=env, capture_output=True, timeout=TIMEOUT_SECONDS,
        start_new_session=True,
    )
    return args_log.read_text().splitlines()


def test_serve_passes_the_complete_chat_template_kwargs_to_the_image_model(served_args):
    assert CHAT_TEMPLATE_KWARGS in served_args


def test_serve_starts_the_pdf_model_on_its_local_port(served_args):
    assert "8001" in served_args
