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


ProjectStatus = Literal["draft", "active", "paused", "completed", "archived"]


class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    project_type: str = Field(min_length=2, max_length=80)
    customer: str = Field(default="", max_length=255)
    description: str = ""
    status: ProjectStatus = "draft"
    progress: int = Field(default=0, ge=0, le=100)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    project_type: str | None = Field(default=None, min_length=2, max_length=80)
    customer: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EnvironmentBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    environment_type: str = Field(min_length=2, max_length=80)
    area_m2: str = Field(default="", max_length=30)
    height_m: str = Field(default="", max_length=30)
    width_m: str = Field(default="", max_length=30)
    length_m: str = Field(default="", max_length=30)
    notes: str = ""


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentRead(EnvironmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MraObjectBase(BaseModel):
    category: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=255)
    brand: str = Field(default="", max_length=120)
    model: str = Field(default="", max_length=120)
    serial_number: str = Field(default="", max_length=120)
    description: str = ""
    status: str = Field(default="active", max_length=30)
    metadata_json: dict = Field(default_factory=dict)


class MraObjectCreate(MraObjectBase):
    pass


class MraObjectRead(MraObjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    environment_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
