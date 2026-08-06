import uuid

from app.models import KnowledgeCard, KnowledgeRevision
from app.services.knowledge_revision_service import KnowledgeRevisionService


class FakeKnowledgeRepository:
    def __init__(self, card: KnowledgeCard) -> None:
        self.card = card

    def get(self, card_id):
        return self.card if self.card.id == card_id else None

    def save(self, card):
        self.card = card
        return card

    def commit(self):
        pass

    def rollback(self):
        pass


class FakeRevisionRepository:
    def __init__(self) -> None:
        self.revisions: list[KnowledgeRevision] = []

    def list_for_card(self, card_id):
        return [item for item in self.revisions if item.card_id == card_id]

    def get(self, card_id, revision_id):
        return next(
            (
                item
                for item in self.revisions
                if item.card_id == card_id and item.id == revision_id
            ),
            None,
        )

    def add(self, *, card_id, action, snapshot, note=""):
        revision = KnowledgeRevision(
            id=uuid.uuid4(),
            card_id=card_id,
            revision_number=len(self.revisions) + 1,
            action=action,
            snapshot=snapshot,
            note=note,
        )
        self.revisions.append(revision)
        return revision


def make_card() -> KnowledgeCard:
    return KnowledgeCard(
        id=uuid.uuid4(),
        code="KC-1",
        title="Titolo corrente",
        category="Test",
        status="draft",
        version="1.0.0",
    )


def test_record_and_restore_revision():
    card = make_card()
    knowledge_repository = FakeKnowledgeRepository(card)
    revision_repository = FakeRevisionRepository()
    service = KnowledgeRevisionService(
        revision_repository,
        knowledge_repository,
    )

    original = service.record(card, action="create")
    card.title = "Titolo modificato"
    service.record(card, action="update")

    restored = service.restore(card.id, original.id)

    assert restored.title == "Titolo corrente"
    assert len(revision_repository.revisions) == 3
    assert revision_repository.revisions[-1].action == "restore"
