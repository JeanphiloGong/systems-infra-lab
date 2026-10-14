import pytest

from labs.storage.wal.framing import decode, encode


def test_each_truncated_byte_retains_complete_prefix() -> None:
    first = {"kind": "set", "tx": "t1", "key": "alice", "value": 90}
    second = {"kind": "commit", "tx": "t1"}
    a, b = encode(first), encode(second)
    assert decode(a + b) == ([first, second], len(a + b), False)
    for cut in range(1, len(b)):
        assert decode(a + b[:cut]) == ([first], len(a), True)
    assert decode(b"") == ([], 0, False)


def test_complete_header_and_payload_corruption_raise() -> None:
    frame = bytearray(encode({"kind": "commit", "tx": "t1"}))
    frame[0] ^= 1
    with pytest.raises(ValueError, match="header"):
        decode(bytes(frame))
    frame = bytearray(encode({"kind": "commit", "tx": "t1"}))
    frame[9] ^= 1
    with pytest.raises(ValueError, match="checksum"):
        decode(bytes(frame))


def test_payload_limit() -> None:
    with pytest.raises(ValueError, match="large"):
        encode({"data": "x" * (1024 * 1024)})
