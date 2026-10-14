from itertools import product

from labs.storage.bloom.filter import BloomFilter, theoretical_false_positive_rate


def sweep(
    bit_counts: list[int], hash_counts: list[int], insertion_counts: list[int],
    probes: int = 10000,
) -> list[dict[str, int | float]]:
    if probes < 1:
        raise ValueError("probes must be positive")
    rows: list[dict[str, int | float]] = []
    for bits, hashes, inserted in product(bit_counts, hash_counts, insertion_counts):
        theory = theoretical_false_positive_rate(bits, hashes, inserted)
        bloom = BloomFilter(bits, hashes)
        for index in range(inserted):
            bloom.add(f"present-{index}")
        false_negatives = sum(not bloom.might_contain(f"present-{index}") for index in range(inserted))
        false_positives = sum(bloom.might_contain(f"absent-{index}") for index in range(probes))
        rows.append({
            "bits": bits, "hashes": hashes, "inserted": inserted,
            "bytes": bloom.bytes_used, "probes": probes,
            "false_positives": false_positives, "false_negatives": false_negatives,
            "theory": theory, "measured": false_positives / probes,
        })
    return rows
