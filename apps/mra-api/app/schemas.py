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

AuthRole = Literal["admin", "editor", "viewer"]
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 1024
DISPLAY_NAME_MIN_LENGTH = 2
DISPLAY_NAME_MAX_LENGTH = 120


def normalize_email_value(value: str) -> str:
    value = value.strip().lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError("Email non valida.")
    local, domain = value.rsplit("@", 1)
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Email non valida.")
    return value


def normalize_display_name_value(value: str) -> str:
    value = value.strip()
    if not DISPLAY_NAME_MIN_LENGTH <= len(value) <= DISPLAY_NAME_MAX_LENGTH:
        raise ValueError("Nome visualizzato non valido.")
    return value


def validate_password_value(value: str) -> str:
    if not PASSWORD_MIN_LENGTH <= len(value) <= PASSWORD_MAX_LENGTH:
        raise ValueError("Password non valida.")
    return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_value(value)


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=DISPLAY_NAME_MIN_LENGTH, max_length=DISPLAY_NAME_MAX_LENGTH)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    role: AuthRole = "viewer"
    must_change_password: bool = True

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return normalize_email_value(value)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return normalize_display_name_value(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_value(value)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=DISPLAY_NAME_MIN_LENGTH, max_length=DISPLAY_NAME_MAX_LENGTH)
    role: AuthRole | None = None
    is_active: bool | None = None
    must_change_password: bool | None = None
    password: str | None = Field(default=None, min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("display_name")
    @classmethod
    def normalize_optional_display_name(cls, value: str | None) -> str | None:
        return normalize_display_name_value(value) if value is not None else None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: AuthRole
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    user: UserRead


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    occurred_at: datetime
    actor_user_id: uuid.UUID | None
    actor_email_snapshot: str | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    outcome: Literal["success", "failure"]
    request_id: uuid.UUID
    changed_fields: list[str]
    changes: dict[str, object]
    metadata_json: dict[str, object]


class AuditEventPage(BaseModel):
    items: list[AuditEventRead]
    next_cursor: str | None = None


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
MraObjectStatus = Literal["active", "maintenance", "inactive", "retired"]


def _strip_required(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Il valore non può essere vuoto.")
    return value


def _normalize_dimension(value: str) -> str:
    value = value.strip().replace(",", ".")
    if not value:
        return ""
    try:
        numeric_value = float(value)
    except ValueError as exc:
        raise ValueError("La dimensione deve essere un numero valido.") from exc
    if numeric_value <= 0:
        raise ValueError("La dimensione deve essere maggiore di zero.")
    return value


class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    project_type: str = Field(min_length=2, max_length=80)
    customer: str = Field(default="", max_length=255)
    description: str = ""
    status: ProjectStatus = "draft"
    progress: int = Field(default=0, ge=0, le=100)

    @field_validator("name", "project_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return _strip_required(value)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    project_type: str | None = Field(default=None, min_length=2, max_length=80)
    customer: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None
    progress: int | None = Field(default=None, ge=0, le=100)

    @field_validator("name", "project_type")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        return _strip_required(value) if value is not None else None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("I campi aggiornati non possono essere null.")
        return self


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

    @field_validator("name", "environment_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return _strip_required(value)

    @field_validator("area_m2", "height_m", "width_m", "length_m")
    @classmethod
    def validate_dimension(cls, value: str) -> str:
        return _normalize_dimension(value)


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    environment_type: str | None = Field(default=None, min_length=2, max_length=80)
    area_m2: str | None = Field(default=None, max_length=30)
    height_m: str | None = Field(default=None, max_length=30)
    width_m: str | None = Field(default=None, max_length=30)
    length_m: str | None = Field(default=None, max_length=30)
    notes: str | None = None

    @field_validator("name", "environment_type")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        return _strip_required(value) if value is not None else None

    @field_validator("area_m2", "height_m", "width_m", "length_m")
    @classmethod
    def validate_optional_dimension(cls, value: str | None) -> str | None:
        return _normalize_dimension(value) if value is not None else None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("I campi aggiornati non possono essere null.")
        return self


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
    status: MraObjectStatus = "active"
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @field_validator("category", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return _strip_required(value)


class MraObjectCreate(MraObjectBase):
    pass


class MraObjectUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=120)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    description: str | None = None
    status: MraObjectStatus | None = None
    metadata_json: dict[str, object] | None = None

    @field_validator("category", "name")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        return _strip_required(value) if value is not None else None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("I campi aggiornati non possono essere null.")
        return self


class MraObjectRead(MraObjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    environment_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
