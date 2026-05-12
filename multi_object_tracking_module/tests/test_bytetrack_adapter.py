from pathlib import Path
import sys


MODULE_PARENT = Path(__file__).resolve().parents[2]
if str(MODULE_PARENT) not in sys.path:
    sys.path.insert(0, str(MODULE_PARENT))


from multi_object_tracking_module.bytetrack_adapter import ByteTrackAdapter


def test_new_track_is_not_marked_missed_in_creation_frame():
    tracker = ByteTrackAdapter()

    tracks = tracker.update([([0.0, 0.0, 20.0, 20.0], 0.95)], frame_id=0)

    assert len(tracks) == 1
    assert tracks[0].track_id == 1
    assert tracker._tracks[0].missed == 0
    assert tracks[0].state == "tentative"


def test_track_keeps_same_id_and_becomes_confirmed():
    tracker = ByteTrackAdapter()

    ids = []
    states = []
    for frame_id, x in enumerate([0.0, 1.0, 2.0]):
        tracks = tracker.update([([x, 0.0, 20.0, 20.0], 0.95)], frame_id=frame_id)
        ids.append(tracks[0].track_id)
        states.append(tracks[0].state)

    assert len(set(ids)) == 1
    assert states == ["tentative", "tentative", "confirmed"]
