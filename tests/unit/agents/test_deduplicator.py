from app.agents.deduplicator import compute_content_hash


def test_same_data_same_hash():
    data = {"city": "Goiânia", "state": "GO", "current_value": 200000}
    assert compute_content_hash(data) == compute_content_hash(data)


def test_different_data_different_hash():
    a = {"city": "Goiânia", "state": "GO", "current_value": 200000}
    b = {"city": "Goiânia", "state": "GO", "current_value": 250000}
    assert compute_content_hash(a) != compute_content_hash(b)


def test_excludes_timestamp_fields():
    base = {"city": "Goiânia", "current_value": 200000}
    with_ts = {**base, "first_seen_at": "2026-01-01", "last_seen_at": "2026-06-01", "content_hash": "old"}
    assert compute_content_hash(base) == compute_content_hash(with_ts)


def test_returns_64_char_hex():
    h = compute_content_hash({"x": 1})
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_key_order_does_not_matter():
    a = {"city": "SP", "state": "SP"}
    b = {"state": "SP", "city": "SP"}
    assert compute_content_hash(a) == compute_content_hash(b)
