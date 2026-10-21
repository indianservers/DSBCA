from datetime import date
from app.professional.schemas import ToolInput
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

SUBJECTS = ["Corporate Tax", "VAT", "Transfer Pricing", "Pillar Two", "IFRS", "Audit"]
TYPES = [
    "Legislation",
    "Cabinet Decision",
    "Ministerial Decision",
    "Official Tax Guidance",
    "Public Clarification",
    "IFRS Standard",
    "Audit Standard",
    "Internal Technical Note",
    "Professional Interpretation",
    "Demonstration Material",
    "Other",
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DocumentInput(Input):
    title: str = Field(min_length=1, max_length=240)
    subject: Literal[
        "Corporate Tax", "VAT", "Transfer Pricing", "Pillar Two", "IFRS", "Audit"
    ]
    issuer: str = Field(min_length=1, max_length=180)
    jurisdiction: str = Field(default="UAE", max_length=80)
    language: str = Field(default="en", max_length=20)
    document_type: str = Field(max_length=80)
    description: str = Field(default="", max_length=5000)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    internal_notes: str = Field(default="", max_length=5000)
    scope: Literal["shared", "organization", "client", "private", "demo"] = "shared"
    organization_id: str | None = None
    company_id: str | None = None
    version: str = Field(min_length=1, max_length=80)
    publication_date: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    applicable_periods: str = Field(default="", max_length=240)

    @model_validator(mode="after")
    def validate_metadata(self):
        if self.document_type not in TYPES:
            raise ValueError("Select a supported document type")
        if (
            self.effective_from
            and self.effective_to
            and self.effective_from > self.effective_to
        ):
            raise ValueError("Effective dates are reversed")
        if (self.scope == "organization") != bool(self.organization_id):
            raise ValueError("Organization scope requires exactly one organization")
        if (self.scope == "client") != bool(self.company_id):
            raise ValueError("Client scope requires exactly one owned company")
        if (self.document_type == "Demonstration Material") != (self.scope == "demo"):
            raise ValueError("Demonstration material must use demo scope")
        return self


class DirectUpload(Input):
    metadata: DocumentInput
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_size: int = Field(gt=0)


class ConfigInput(Input):
    name: str = Field(default="DSBCA Research", min_length=1, max_length=100)
    system_instructions: str = Field(min_length=100, max_length=12000)
    chat_model: str = Field(default="", max_length=100)
    fast_model: str = Field(default="", max_length=100)
    embedding_model: str = Field(default="", max_length=100)
    retrieval_top_k: int = Field(default=8, ge=1, le=16)
    max_output_tokens: int = Field(default=1800, ge=128, le=4000)
    minimum_evidence_score: float = Field(default=0.25, ge=0, le=1)
    history_window: int = Field(default=8, ge=0, le=20)
    search_mode: Literal["approved_pdfs"] = "approved_pdfs"
    allowed_subjects: list[str] = Field(default_factory=lambda: SUBJECTS.copy())
    feedback_enabled: bool = True
    citations_required: Literal[True] = True
    rerank_enabled: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    temperature_supported: bool = False
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)


class ChatInput(Input):
    application_tool: ToolInput | None = None
    conversation_id: str
    request_id: str = Field(min_length=10, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    question: str = Field(min_length=3, max_length=6000)
    subject: Literal[
        "Corporate Tax", "VAT", "Transfer Pricing", "Pillar Two", "IFRS", "Audit"
    ] = "Corporate Tax"
    jurisdiction: str = Field(default="UAE", max_length=80)
    period_start: date | None = None
    period_end: date | None = None
    issuer: str | None = Field(default=None, max_length=180)
    include_demo: bool = False

    @model_validator(mode="after")
    def dates(self):
        if bool(self.period_start) != bool(self.period_end):
            raise ValueError("Provide both start and end of the research period")
        if self.period_start and self.period_start > self.period_end:
            raise ValueError("Research period is reversed")
        return self


class Claim(Input):
    text: str = Field(min_length=1, max_length=5000)
    evidence_ids: list[str] = Field(min_length=1, max_length=8)
    supporting_quotes: list[str] = Field(min_length=1, max_length=8)


class GroundedAnswer(Input):
    claims: list[Claim] = Field(max_length=12)
    missing_information: list[str] = Field(max_length=8)
    limitations: list[str] = Field(max_length=8)


class FeedbackInput(Input):
    message_id: str
    rating: Literal[-1, 1]
    comment: str = Field(default="", max_length=1000)


class ConversationInput(Input):
    title: str = Field(default="New research", min_length=1, max_length=160)
