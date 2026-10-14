from labs.storage.bplus_tree.experiments import compare_accesses, interrupted_save


def test_logical_pages_use_same_query_and_record_size() -> None:
    report = compare_accesses(list(range(1000)), [17, 500, 999])
    assert report["array_page_reads"] > 0
    assert report["tree_page_reads"] > 0
    assert report["probes"] == 3
    assert compare_accesses([1, 2], [1, 2, 3]) == {
        "probes": 3, "array_page_reads": 3, "tree_page_reads": 3,
    }


def test_interrupted_page_write_is_rejected(tmp_path) -> None:
    path = tmp_path / "tree.pages"
    partial_bytes = interrupted_save(path)
    assert partial_bytes == path.stat().st_size == 256
