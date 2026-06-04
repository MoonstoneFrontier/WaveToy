import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:
        from tests.test_performance_timeline_undo import _install_qt_stubs

        _install_qt_stubs()
        from PySide6.QtWidgets import QApplication
    app = QApplication.instance() if hasattr(QApplication, "instance") else None
    if app is None:
        app = QApplication([])
    return app
