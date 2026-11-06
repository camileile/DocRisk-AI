import os
import tempfile

import pytest

# Banco e uploads de teste em pasta temporária, antes de importar docrisk_core.config.
os.environ["DOCRISK_DATA_DIR"] = tempfile.mkdtemp(prefix="docrisk-test-")
os.environ.setdefault("AI_PROVIDER", "textlayer")
os.environ.setdefault("DOCRISK_SYNC", "1")


@pytest.fixture(autouse=True)
def demo_mode_for_tests(monkeypatch):
    from docrisk_core import config

    monkeypatch.setattr(config, "DEMO_MODE", True)
