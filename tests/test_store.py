from pathlib import Path

from app.case_runtime import CaseCatalogue, InterviewSession
from app.store import SessionStore


def test_attempt_survives_a_new_store_instance(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    catalogue = CaseCatalogue.from_reservoir(root)
    world = catalogue.default_case
    database = tmp_path / "casecall.db"
    original = InterviewSession(id="attempt-1", case=world, mode="realistic")
    original.add_interviewer_turn("Opening")
    original.add_interviewer_turn("Candidate question")

    SessionStore(database).save(original)
    restored = SessionStore(database).get("attempt-1", catalogue)

    assert restored is not None
    assert restored.messages == original.messages
    assert restored.mode == "realistic"
