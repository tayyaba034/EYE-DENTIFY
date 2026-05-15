from pathlib import Path
import sys


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


def test_run_tracking_imports_from_module_directory():
    import run_tracking

    assert run_tracking.main is not None
