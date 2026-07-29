from app.persistence.in_memory_repository import InMemoryMatchRepository


def test_new_match_starts_empty_and_unfinished():
    repo = InMemoryMatchRepository()
    repo.create("m1")

    assert repo.exists("m1")
    assert repo.get_events("m1") == []
    assert repo.is_finished("m1") is False


def test_unknown_match_does_not_exist():
    repo = InMemoryMatchRepository()
    assert repo.exists("nope") is False


def test_append_and_get_events():
    repo = InMemoryMatchRepository()
    repo.create("m1")
    repo.append_event("m1", {"minute": 2, "type": "kickoff"})
    repo.append_event("m1", {"minute": 4, "type": "shot"})

    assert repo.get_events("m1") == [{"minute": 2, "type": "kickoff"}, {"minute": 4, "type": "shot"}]


def test_get_events_since_index_returns_only_new_ones():
    repo = InMemoryMatchRepository()
    repo.create("m1")
    repo.append_event("m1", {"minute": 2})
    repo.append_event("m1", {"minute": 4})
    repo.append_event("m1", {"minute": 6})

    assert repo.get_events("m1", since_index=2) == [{"minute": 6}]


def test_mark_finished():
    repo = InMemoryMatchRepository()
    repo.create("m1")
    repo.mark_finished("m1")

    assert repo.is_finished("m1") is True


def test_two_matches_are_independent():
    repo = InMemoryMatchRepository()
    repo.create("m1")
    repo.create("m2")
    repo.append_event("m1", {"minute": 2})

    assert repo.get_events("m1") == [{"minute": 2}]
    assert repo.get_events("m2") == []
