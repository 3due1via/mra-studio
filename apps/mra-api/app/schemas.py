import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

KnowledgeStatus = Literal[
    "draft",
    "review",
    "verified",
    "approved",
    "published",
    "archived",
    "rejected",
]

KnowledgeRelationType = Literal[
    "related_to",
    "requires",
    "uses",
    "replaces",
    "part_of",
    "references",
]


class KnowledgeCardBase(BaseModel):
    code: str = Field(min_length=3, max_length=64)
    title: str = Field(min_length=2, max_length=255)
    category: str = Field(min_length=2, max_length=120)
    status: KnowledgeStatus = "draft"
    version: str = Field(default="1.0.0", min_length=5, max_length=30)
    summary: str = ""
    symptoms: str = ""
    causes: str = ""
    diagnosis: str = ""
    procedure: str = ""
    tools: str = ""
    safety: str = ""

    @field_validator("code", "title", "category")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Il valore non può essere vuoto.")
        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class KnowledgeCardCreate(KnowledgeCardBase):
    pass


class KnowledgeCardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    category: str | None = Field(default=None, min_length=2, max_length=120)
    status: KnowledgeStatus | None = None
    version: str | None = Field(default=None, min_length=5, max_length=30)
    summary: str | None = None
    symptoms: str | None = None
    causes: str | None = None
    diagnosis: str | None = None
    procedure: str | None = None
    tools: str | None = None
    safety: str | None = None


class KnowledgeCardRead(KnowledgeCardBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class KnowledgeRelationCreate(BaseModel):
    target_id: uuid.UUID
    relation_type: KnowledgeRelationType = "related_to"
    note: str = Field(default="", max_length=1000)


class KnowledgeRelationRead(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    relation_type: KnowledgeRelationType
    note: str
    target_code: str
    target_title: str
    target_category: str
    created_at: datetime


class KnowledgeRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    card_id: uuid.UUID
    revision_number: int
    action: str
    note: str
    snapshot: dict[str, str]
    created_at: datetime
