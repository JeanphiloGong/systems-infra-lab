import json
from struct import Struct

CODE = Struct("<H")


def encode_regions(values: list[str | None]) -> tuple[bytes, bytes]:
    dictionary: list[str | None] = [None]
    positions: dict[str | None, int] = {None: 0}
    output = bytearray()
    for value in values:
        if value is not None and not isinstance(value, str):
            raise ValueError("region must be text or None")
        if value not in positions:
            if len(dictionary) == 65536:
                raise ValueError("too many dictionary values")
            positions[value] = len(dictionary)
            dictionary.append(value)
        output.extend(CODE.pack(positions[value]))
    return json.dumps(dictionary, ensure_ascii=False).encode("utf-8"), bytes(output)


def decode_regions(dictionary_bytes: bytes, codes: bytes) -> list[str | None]:
    dictionary = json.loads(dictionary_bytes)
    if not isinstance(dictionary, list) or not dictionary or dictionary[0] is not None:
        raise ValueError("dictionary must reserve zero for None")
    if any(not isinstance(value, str) for value in dictionary[1:]):
        raise ValueError("invalid dictionary value")
    if len(codes) % CODE.size:
        raise ValueError("partial dictionary code")
    result: list[str | None] = []
    for offset in range(0, len(codes), CODE.size):
        index = CODE.unpack_from(codes, offset)[0]
        if index >= len(dictionary):
            raise ValueError("dictionary code outside table")
        result.append(dictionary[index])
    return result
