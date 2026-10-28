from app.services.consultation_state import ALLOWED


def test_terminal_states():
    assert ALLOWED["COMPLETED"] == set()
    assert ALLOWED["CANCELLED"] == set()


def test_valid_path():
    assert "CONFIRMED" in ALLOWED["BOOKED"]
    assert "IN_PROGRESS" in ALLOWED["CONFIRMED"]
    assert "COMPLETED" in ALLOWED["IN_PROGRESS"]


def test_cannot_restart():
    assert "IN_PROGRESS" not in ALLOWED["COMPLETED"]
