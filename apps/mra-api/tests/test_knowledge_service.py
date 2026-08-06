import uuid
from copy import deepcopy

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import KnowledgeCard
from app.schemas import KnowledgeCardCreate, KnowledgeCardUpdate
from app.services.knowledge_service import (
    KnowledgeCardCodeConflictError,
    KnowledgeCardNotFoundError,
    KnowledgePersistenceError,
    KnowledgeService,
)


class FakeKnowledgeRepository:
    def __init__(self) -> None:
        self.cards: dict[uuid.UUID, KnowledgeCard] = {}
        self.pending: dict[uuid.UUID, KnowledgeCard] = {}
        self.rollback_called = False

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
        card = self.cards.get(card_id)
        return deepcopy(card) if card is not None else None

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
        self.pending[card.id] = card
        return card

    def save(self, card):
        self.pending[card.id] = card
        return card

    def delete(self, card):
        self.pending[card.id] = None

    def commit(self):
        for card_id, card in self.pending.items():
            if card is None:
                self.cards.pop(card_id, None)
            else:
                self.cards[card_id] = deepcopy(card)
        self.pending.clear()

    def rollback(self):
        self.rollback_called = True
        self.pending.clear()


class FailingRevisionService:
    def record(self, card, *, action, note=""):
        raise IntegrityError("insert revision", {}, Exception("revision failed"))


class UnexpectedFailingRevisionService:
    def record(self, card, *, action, note=""):
        raise RuntimeError("unexpected revision failure")


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


def test_create_rolls_back_when_revision_fails():
    repository = FakeKnowledgeRepository()
    service = KnowledgeService(repository, revision_service=FailingRevisionService())

    with pytest.raises(KnowledgePersistenceError):
        service.create_card(payload())

    assert repository.cards == {}
    assert repository.pending == {}
    assert repository.rollback_called is True


def test_update_rolls_back_when_revision_fails():
    repository = FakeKnowledgeRepository()
    created = KnowledgeService(repository).create_card(payload())
    service = KnowledgeService(repository, revision_service=FailingRevisionService())

    with pytest.raises(KnowledgePersistenceError):
        service.update_card(
            created.id,
            KnowledgeCardUpdate(title="Modifica non persistita"),
        )

    assert repository.cards[created.id].title == "Resistenza"
    assert repository.rollback_called is True


def test_unexpected_error_also_rolls_back():
    repository = FakeKnowledgeRepository()
    service = KnowledgeService(
        repository,
        revision_service=UnexpectedFailingRevisionService(),
    )

    with pytest.raises(RuntimeError, match="unexpected revision failure"):
        service.create_card(payload())

    assert repository.cards == {}
    assert repository.rollback_called is True
