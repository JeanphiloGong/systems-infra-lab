from __future__ import annotations

import subprocess
import sys

import pytest

from labs.replication.leader_follower import v0, v1, v2, v3, v4


def test_v0_applies_order_and_keeps_progress_after_restart(tmp_path) -> None:
    leader = v0.Leader()
    follower = v0.Follower()
    entries = [leader.write("order", "created"), leader.write("order", "paid")]
    follower.apply(entries)
    follower.restart()
    assert follower.applied_position == 2
    assert follower.data == {"order": "paid"}
    with pytest.raises(ValueError):
        follower.apply([entries[0]])
    checkpoint = tmp_path / "follower.json"
    persisted = v0.Follower(checkpoint)
    persisted.apply(entries)
    recovered = v0.Follower(checkpoint)
    assert recovered.applied_position == 2
    assert recovered.data == {"order": "paid"}


def test_v0_writer_and_receiver_are_separate_processes(tmp_path) -> None:
    checkpoint = tmp_path / "follower.json"
    script = v0.__file__
    writer = subprocess.run(
        [sys.executable, script, "--writer", str(checkpoint)],
        capture_output=True, text=True, check=True,
    )
    receiver = subprocess.run(
        [sys.executable, script, "--reader", str(checkpoint)],
        capture_output=True, text=True, check=True,
    )
    assert writer.stdout.strip() == '{"position": 2, "data": {"order-1": "paid"}}'
    assert receiver.stdout.strip() == writer.stdout.strip()


def test_v1_exposes_stale_read_until_apply_step() -> None:
    leader = v1.Leader()
    follower = v1.Follower()
    entry = leader.write("order", "paid")
    follower.receive([entry])
    assert follower.data == {}
    follower.apply_one()
    assert follower.data["order"] == "paid"


def test_v2_barrier_wait_timeout_and_leader_read() -> None:
    leader = v2.Leader()
    follower = v2.Follower()
    position = leader.write("order", "paid")
    follower.receive(leader.log)
    assert v2.read_from_leader(leader, "order") == "paid"
    with pytest.raises(TimeoutError):
        follower.read_after("order", position, timeout_steps=0)
    assert follower.read_after("order", position, timeout_steps=1) == "paid"


def test_v3_ack_modes_have_different_loss_boundaries() -> None:
    follower = v3.Follower()
    leader = v3.Leader()
    async_entry = leader.write("order", "created", v3.AckMode.ASYNC, follower)
    assert leader.confirmed_position == 0
    assert leader.fail_before_replication() == [async_entry]
    follower.apply([async_entry])
    confirmed = leader.write("order", "paid", v3.AckMode.FOLLOWER, follower)
    assert leader.confirmed_position == confirmed.position
    assert follower.data["order"] == "paid"


def test_v3_follower_ack_measures_delay_and_persists_data(tmp_path) -> None:
    follower = v3.Follower(latency_ms=2, state_path=tmp_path / "follower.json")
    leader = v3.Leader()
    entry = leader.write("order", "paid", v3.AckMode.FOLLOWER, follower)
    assert leader.last_confirmation_latency_ms >= 2
    recovered = v3.Follower(state_path=tmp_path / "follower.json")
    assert recovered.applied_position == entry.position
    assert recovered.data == {"order": "paid"}


def test_v4_resume_and_duplicate_delivery_are_safe() -> None:
    leader = v4.Leader()
    leader.write("order", "created")
    leader.write("order", "paid")
    follower = v4.Follower()
    follower.catch_up(leader.log, stop_after=1)
    follower.catch_up(leader.log)
    follower.catch_up(leader.log)
    assert follower.applied_position == 2
    assert follower.data["order"] == "paid"
    with pytest.raises(ValueError):
        follower.apply([v4.Entry(4, "order", "shipped")])


def test_v4_stop_resume_recovers_from_a_fresh_process(tmp_path) -> None:
    leader = v4.Leader()
    leader.write("order", "created")
    leader.write("order", "paid")
    checkpoint = tmp_path / "follower.json"
    v4.Follower(checkpoint).catch_up(leader.log, stop_after=1)
    recovered = v4.Follower(checkpoint)
    recovered.catch_up(leader.log)
    assert recovered.applied_position == 2
    assert recovered.data == {"order": "paid"}
