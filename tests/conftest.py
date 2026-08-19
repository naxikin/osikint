import importlib.util
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _load_legacy():
    path = os.path.join(PROJECT_ROOT, "social_osint.py")
    spec = importlib.util.spec_from_file_location("social_osint_legacy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def legacy():
    return _load_legacy()


@pytest.fixture()
def sample_image(tmp_path):
    from PIL import Image

    image = Image.new("RGB", (64, 64), color=(90, 30, 200))
    path = tmp_path / "sample.jpg"
    image.save(path)
    return str(path)
