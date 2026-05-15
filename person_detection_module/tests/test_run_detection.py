from pathlib import Path
import sys


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


def test_run_detection_imports_from_module_directory():
    import run_detection

    assert run_detection.parse_args is not None
