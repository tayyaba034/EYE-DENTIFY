from pathlib import Path
import shutil

import numpy as np

from output_delivery_module import OutputDeliveryEngine


def test_output_delivery_creates_snapshot_record():
    snapshot_dir = Path("runtime/artifacts/test_output_delivery")
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)

    engine = OutputDeliveryEngine(snapshot_dir=str(snapshot_dir))
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[10:50, 10:50] = 255

    record = engine.create_record(
        track_id=9,
        confidence=0.88,
        explanation="test explanation",
        frame=frame,
        bbox=[10, 10, 40, 40],
    )

    assert record.track_id == 9
    assert record.snapshot is not None
    assert Path(record.snapshot).exists()
