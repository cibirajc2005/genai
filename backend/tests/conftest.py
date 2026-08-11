"""Keep automated tests isolated from the developer's local document database."""

import shutil
import tempfile
import uuid
from pathlib import Path

from app.core.config import settings

_test_root = Path(tempfile.gettempdir()) / f"genai-tests-{uuid.uuid4()}"
_test_root.mkdir(parents=True, exist_ok=True)
object.__setattr__(settings, "supabase_database_url", "")
object.__setattr__(settings, "supabase_url", "")
object.__setattr__(settings, "supabase_secret_key", "")
object.__setattr__(settings, "database_path", _test_root / "app.db")
object.__setattr__(settings, "documents_path", _test_root / "documents")


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_test_root, ignore_errors=True)
