def visible(versions: list[tuple[int, bool]], snapshot: int) -> bool:
    """Read an append-ordered committed-version list at a logical timestamp."""
    for committed_at, value in reversed(versions):
        if committed_at <= snapshot:
            return value
    raise LookupError("no visible version")


def main() -> None:
    versions = [(1, True)]
    old_snapshot = 1
    versions.append((2, False))
    print(visible(versions, old_snapshot), visible(versions, 2))


if __name__ == "__main__":
    main()
