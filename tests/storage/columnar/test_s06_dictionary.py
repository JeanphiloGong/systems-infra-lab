from pathlib import Path

import pytest

from labs.storage.columnar.dictionary import encode_regions, decode_regions


def test_dictionary_preserves_null_and_saves_low_cardinality_space() -> None:
    values = ["east", "west", None] * 100
    dictionary, codes = encode_regions(values)
    assert decode_regions(dictionary, codes) == values
    assert len(dictionary) + len(codes) < len(values) * 12
    assert encode_regions([])[1] == b""


def test_invalid_code_and_partial_code_rejected() -> None:
    dictionary, _ = encode_regions(["east"])
    for codes in (b"\xff\xff", b"x"):
        with pytest.raises(ValueError):
            decode_regions(dictionary, codes)
