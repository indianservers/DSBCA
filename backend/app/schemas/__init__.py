from datetime import date, datetime
from typing import Literal, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(Input):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=120)


class Refresh(Input):
    refresh_token: str = Field(min_length=20, max_length=500)


class ResetRequest(Input):
    email: EmailStr


class Reset(Input):
    token: str = Field(min_length=20, max_length=500)
    password: str = Field(min_length=12, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class CompanyInput(Input):
    profile_data: dict = Field(default_factory=dict)
    name: str = Field(min_length=1, max_length=180)
    trn: str | None = Field(default=None, max_length=32)


class PersonInput(Input):
    details: dict = Field(default_factory=dict)
    name: str = Field(min_length=1, max_length=120)
    role: Literal[
        "partner", "manager", "shareholder", "director", "signatory", "employee"
    ]


class DocumentInput(Input):
    title: str = Field(min_length=1, max_length=180)
    category: Literal[
        "Trade Licence", "Passport", "Emirates ID", "Residence Visa", "Tenancy Contract"
    ]
    expires_on: date
    person_id: str | None = None
    storage_key: str | None = Field(default=None, max_length=400)


class ReminderInput(Input):
    title: str = Field(min_length=1, max_length=180)
    due_on: date
    document_id: str | None = None
    completed: bool = False


class Preferences(Input):
    categories: list[str] = Field(default_factory=list, max_length=30)
    in_app: bool = True


class CategoryInput(Input):
    name: str = Field(min_length=1, max_length=100)


class ContentInput(Input):
    video_category_id: str | None = None
    metadata_extra: dict = Field(default_factory=dict)
    visibility: Literal["public", "authenticated"] = "public"
    publish_at: datetime | None = None
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(default="", max_length=100000)
    category_id: str | None = None
    status: Literal["draft", "published", "archived"] = "draft"
    demo: bool = False
    duration_seconds: int = Field(default=0, ge=0)
    media_url: str | None = None
    download_url: str | None = None
    reading_minutes: int = Field(default=4, ge=1)
    source_url: str | None = None
    starts_at: datetime | None = None
    join_url: str | None = None

    @field_validator("metadata_extra")
    @classmethod
    def content_metadata(cls, value):
        from zoneinfo import ZoneInfo

        if len(str(value)) > 30000:
            raise ValueError("Metadata too large")
        for key, low, high in [
            ("capacity", 0, 100000),
            ("duration_minutes", 1, 1440),
            ("display_order", 0, 1000000),
        ]:
            if key in value and (
                type(value[key]) is not int or not low <= value[key] <= high
            ):
                raise ValueError("Invalid " + key)
        if value.get("timezone"):
            try:
                ZoneInfo(value["timezone"])
            except Exception:
                raise ValueError("Use an IANA timezone")
        for key in ["thumbnail_url", "recording_url"]:
            if value.get(key) and not str(value[key]).startswith("https://"):
                raise ValueError("HTTPS media links required")
        return value

    @field_validator("media_url", "download_url", "source_url", "join_url")
    @classmethod
    def https_only(cls, value):
        if value is not None and not value.startswith("https://"):
            raise ValueError("Use an HTTPS URL")
        return value


class ChapterInput(Input):
    asset_id: str | None = None
    body: str = Field(default="", max_length=100000)
    publication_id: str
    title: str = Field(min_length=1, max_length=240)
    position: int = Field(ge=1)
    pages: int = Field(default=0, ge=0)
    download_url: str | None = None


class NotificationInput(Input):
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    deep_link: str = "/updates"
    status: Literal["draft", "published"] = "draft"
    demo: bool = False

    @field_validator("deep_link")
    @classmethod
    def local_route(cls, v):
        if not v.startswith("/") or v.startswith("//") or "\\" in v or ":" in v:
            raise ValueError("Internal paths only")
        return v


class AccountInput(Input):
    status: Literal["active", "suspended"]
    roles: list[Literal["user", "content_editor", "admin", "super_admin"]]


class SettingInput(Input):
    key: str = Field(min_length=1, max_length=100)
    value: dict


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class ContentResponse(RecordResponse):
    video_category_id: str | None = None
    metadata_extra: dict = Field(default_factory=dict)
    visibility: str = "public"
    publish_at: datetime | None = None
    title: str
    body: str
    category_id: str | None
    status: str
    demo: bool
    duration_seconds: int | None = None
    media_url: str | None = None
    download_url: str | None = None
    reading_minutes: int | None = None
    source_url: str | None = None
    starts_at: datetime | None = None
    join_url: str | None = None
    read_at: datetime | None = None


class CompanyResponse(RecordResponse):
    profile_data: dict = Field(default_factory=dict)
    name: str
    owner_id: str
    trn: str | None


class CategoryResponse(RecordResponse):
    name: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    status: str
    roles: list[str]
