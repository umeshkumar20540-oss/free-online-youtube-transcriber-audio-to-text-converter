"""
Automated unit test for JobState event buffer, replay, and reconnection.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import JobState, active_jobs, jobs_lock


async def test_reconnect_logic():
    print("Testing auto-reconnect event buffer & replay...")
    loop = asyncio.get_running_loop()

    job_id = "test_job_replay"
    job = JobState(job_id, {"url": "https://youtu.be/test"})
    with jobs_lock:
        active_jobs[job_id] = job

    # 1. Add initial events
    job.add_event({"type": "status", "message": "Downloading 10%", "progress": 10}, loop)
    job.add_event({"type": "status", "message": "Downloading 25%", "progress": 25}, loop)
    job.add_event({"type": "segment", "segment": {"id": 1, "start": 0.0, "end": 2.0, "text": "First segment"}}, loop)
    job.add_event({"type": "segment", "segment": {"id": 2, "start": 2.0, "end": 4.0, "text": "Second segment"}}, loop)

    assert len(job.events) == 4
    for idx, evt in enumerate(job.events):
        assert evt["event_id"] == idx

    # 2. Simulate client who disconnected after event_id 1
    missed = job.get_events_since(last_event_id=1)
    assert len(missed) == 2
    assert missed[0]["event_id"] == 2
    assert missed[1]["event_id"] == 3
    assert missed[0]["segment"]["text"] == "First segment"
    assert missed[1]["segment"]["text"] == "Second segment"

    # 3. Simulate more events arriving while client is reconnecting
    job.add_event({"type": "segment", "segment": {"id": 3, "start": 4.0, "end": 6.0, "text": "Third segment"}}, loop)
    job.add_event({"type": "completed", "progress": 100, "full_text": "Completed transcript"}, loop)

    assert job.status == "completed"

    # 4. Client reconnects after event_id 3 (e.g. saw event 3, then disconnected)
    replayed_after_3 = job.get_events_since(last_event_id=3)
    assert len(replayed_after_3) == 2
    assert replayed_after_3[0]["event_id"] == 4
    assert replayed_after_3[1]["event_id"] == 5
    assert replayed_after_3[1]["type"] == "completed"

    print("[OK] Auto-reconnect and replay logic passed perfectly!")


if __name__ == "__main__":
    asyncio.run(test_reconnect_logic())
