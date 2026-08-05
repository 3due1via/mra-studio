import uuid

import pytest

from app.models import KnowledgeCard
from app.schemas import KnowledgeCardCreate, KnowledgeCardUpdate
from app.services.knowledge_service import (
    KnowledgeCardCodeConflictError,
    KnowledgeCardNotFoundError,
    KnowledgeService,
)


class FakeKnowledgeRepository:
    def __init__(self) -> None:
        self.cards: dict[uuid.UUID, KnowledgeCard] = {}

    def list(self, *, search=None, status_filter=None):
        cards = list(self.cards.values())
        if search:
            term = search.lower()
            cards = [
                card
                for card in cards
                if term in card.code.lower()
                or term in card.title.lower()
                or term in card.category.lower()
            ]
        if status_filter:
            cards = [
                card
                for card in cards
                if card.status == status_filter
            ]
        return cards

    def get(self, card_id):
        return self.cards.get(card_id)

    def get_by_code(self, code):
        return next(
            (
                card
                for card in self.cards.values()
                if card.code == code
            ),
            None,
        )

    def add(self, card):
        if card.id is None:
            card.id = uuid.uuid4()
        self.cards[card.id] = card
        return card

    def save(self, card):
        self.cards[card.id] = card
        return card

    def delete(self, card):
        del self.cards[card.id]


def payload(code: str = "KC-000001"):
    return KnowledgeCardCreate(
        code=code,
        title="Resistenza",
        category="Componenti",
        summary="Componente passivo.",
    )


def test_create_and_get_card():
    repository = FakeKnowledgeRepository()
    service = KnowledgeService(repository)

    created = service.create_card(payload())

    assert created.id is not None
    assert service.get_card(created.id).code == "KC-000001"


def test_duplicate_code_is_rejected():
    repository = FakeKnowledgeRepository()
    service = KnowledgeService(repository)
    service.create_card(payload())

    with pytest.raises(KnowledgeCardCodeConflictError):
        service.create_card(payload())


def test_update_card():
    repository = FakeKnowledgeRepository()
    service = KnowledgeService(repository)
    created = service.create_card(payload())

    updated = service.update_card(
        created.id,
        KnowledgeCardUpdate(title="Resistenza elettrica"),
    )

    assert updated.title == "Resistenza elettrica"


def test_delete_card():
    repository = FakeKnowledgeRepository()
    service = KnowledgeService(repository)
    created = service.create_card(payload())

    service.delete_card(created.id)

    with pytest.raises(KnowledgeCardNotFoundError):
        service.get_card(created.id)
