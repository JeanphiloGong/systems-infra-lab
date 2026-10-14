import pytest
import os
import subprocess
import sys

from labs.storage.bloom.filter import BloomFilter


def test_inserted_keys_have_no_false_negatives() -> None:
    bloom = BloomFilter(1024, 4)
    for key in ("a", "b", "订单-1"):
        bloom.add(key)
    assert all(bloom.might_contain(key) for key in ("a", "b", "订单-1"))
    assert bloom.bytes_used == 128


def test_invalid_parameters_rejected() -> None:
    with pytest.raises(ValueError):
        BloomFilter(0, 1)
    with pytest.raises(ValueError):
        BloomFilter(8, 0)


def test_hash_mapping_survives_different_process_hash_seeds() -> None:
    code = "from labs.storage.bloom.filter import BloomFilter; b=BloomFilter(1024,4); b.add('stable'); print(b.array.hex())"
    outputs = []
    for seed in ("1", "999"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        outputs.append(subprocess.check_output([sys.executable, "-c", code], env=env, text=True))
    assert outputs[0] == outputs[1]
