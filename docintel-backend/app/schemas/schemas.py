from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ---- Auth Schemas ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    organization_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Document Schemas ----
class DocumentResponse(BaseModel):
    id: UUID
    file_name: str
    page_count: int
    file_size: int
    status: str
    upload_date: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ---- Chat / Query Schemas ----
class ChatRequest(BaseModel):
    document_id: UUID
    question: str
    mode: str = "normal"  # normal, deep


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    response_time_ms: float


# ---- Summary Schemas ----
class SummaryRequest(BaseModel):
    document_id: UUID
    summary_type: str = "short"  # short, executive, exam


class SummaryResponse(BaseModel):
    id: UUID
    document_id: UUID
    summary_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Comparison Schemas ----
class CompareRequest(BaseModel):
    document_a_id: UUID
    document_b_id: UUID


class CompareResponse(BaseModel):
    similarity_score: float
    additions: int
    removals: int
    modifications: int
    analysis: str
    diff_sections: List[dict] = []


# ---- Question Generation Schemas ----
class QuestionGenRequest(BaseModel):
    document_id: UUID
    num_questions: int = 10
    difficulty: str = "medium"  # easy, medium, hard


class GeneratedQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    difficulty: str
    source_page: Optional[int] = None


class QuestionGenResponse(BaseModel):
    questions: List[GeneratedQuestion]


# ---- Export Schemas ----
class ExportRequest(BaseModel):
    document_id: UUID
    export_type: str = "pdf"  # pdf, json, text
    content_type: str = "full"  # full, summary, questions, chat


class ExportResponse(BaseModel):
    id: UUID
    export_type: str
    file_path: str
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Analytics Schemas ----
class AnalyticsResponse(BaseModel):
    total_documents: int
    total_queries: int
    total_exports: int
    avg_response_time: float
    accuracy_score: float
    weekly_queries: List[int]
    storage_used_bytes: int
