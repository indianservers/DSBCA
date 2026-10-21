from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CalculationInput(Input):
    inputs: dict = Field(default_factory=dict)
    rule_id: str | None = None
    save: bool = False
    title: str = Field(default="Saved calculation", min_length=1, max_length=180)


class RuleInput(Input):
    code: str = Field(max_length=80)
    version: str = Field(min_length=1, max_length=60)
    category: Literal["calculator", "compliance"] = "calculator"
    valid_from: date
    valid_to: date | None = None
    parameters: dict
    sources: list[dict] = Field(min_length=1, max_length=20)
    validation_cases: list[dict] = Field(min_length=1, max_length=40)


class ProgressInput(Input):
    position: int = Field(default=0, ge=0, le=100000000)
    completed: bool = False


class BookmarkInput(Input):
    saved: bool = True


class PathInput(Input):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=10000)
    subject: str = Field(max_length=80)
    status: Literal["draft", "published", "archived"] = "draft"
    items: list[dict] = Field(default_factory=list, max_length=200)


class DocumentChange(Input):
    title: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=50)
    expires_on: date
    person_id: str | None = None
    details: dict = Field(default_factory=dict)
    status: Literal[
        "active", "renewed", "archived", "not_applicable", "needs_review"
    ] = "active"

    @model_validator(mode="after")
    def document_dates(self):
        if len(str(self.details)) > 20000:
            raise ValueError("Document details too large")
        if self.details.get("issue_date"):
            if date.fromisoformat(self.details["issue_date"]) > self.expires_on:
                raise ValueError("Issue date follows expiry date")
        return self


class ReminderSettings(Input):
    days: list[int] = Field(default_factory=lambda: [30, 7, 0], max_length=20)
    channels: list[Literal["in_app", "email", "push"]] = Field(
        default_factory=lambda: ["in_app"], max_length=3
    )
    enabled: bool = True

    @field_validator("days")
    @classmethod
    def valid_days(cls, v):
        if any(d < 0 or d > 730 for d in v):
            raise ValueError("Use 0–730 days before")
        return sorted(set(v), reverse=True)


class ChannelSettings(Input):
    in_app: bool = True
    email: bool = False
    push: bool = False


class TokenInput(Input):
    token: str = Field(min_length=20, max_length=4096)
    platform: Literal["android", "ios", "web"]


class ObligationInput(Input):
    title: str = Field(min_length=1, max_length=180)
    period_start: date | None = None
    period_end: date | None = None
    due_on: date | None = None
    rule_id: str | None = None
    facts_confirmed: bool = False
    facts: dict = Field(default_factory=dict)


class StateInput(Input):
    status: Literal[
        "pending", "completed", "not_applicable", "needs_review", "superseded"
    ]


class ToolInput(Input):
    name: str = Field(max_length=80)
    arguments: dict = Field(default_factory=dict)
    request_id: str = Field(min_length=10, max_length=80)
    confirmation_token: str | None = None


class SubscriptionInput(Input):
    subjects: list[str] = Field(max_length=30)


class ReviewInput(Input):
    action: Literal[
        "review", "approve", "publish", "supersede", "archive", "flag_sources"
    ]
    knowledge_version_ids: list[str] = Field(default_factory=list, max_length=50)
    learning_resource_ids: list[str] = Field(default_factory=list, max_length=50)
    effective_on: date | None = None


class CampaignInput(Input):
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=5000)
    subject: str = Field(min_length=1, max_length=100)
    scheduled_at: datetime
    template_key: str | None = None
    confirmed: bool = False


class ReorderInput(Input):
    chapter_ids: list[str] = Field(max_length=500)


class VideoCategoryInput(Input):
    subject_id: str
    name: str = Field(min_length=1, max_length=100)
