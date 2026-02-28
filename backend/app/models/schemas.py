"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class TemplateType(str, Enum):
    PROFESSIONAL = "professional"
    STARTUP = "startup"
    ACADEMIC = "academic"
    MINIMAL = "minimal"
    DARK_MODERN = "dark_modern"


class ToneType(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    ACADEMIC = "academic"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Request Models
class StartSessionRequest(BaseModel):
    """Request to start a new session."""
    template: TemplateType = TemplateType.PROFESSIONAL
    tone: ToneType = ToneType.PROFESSIONAL


class GenerateRequest(BaseModel):
    """Request to generate a presentation."""
    session_id: str
    topic: str = Field(..., min_length=3, max_length=500)
    num_slides: int = Field(default=2, le=15)
    additional_context: Optional[str] = None


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class GoogleLoginRequest(BaseModel):
    id_token: str


class UpdateSlideRequest(BaseModel):
    """Request to update a specific slide."""
    session_id: str
    slide_number: int = Field(..., ge=1)
    instruction: str = Field(..., min_length=3, max_length=1000)


class RollbackSlideRequest(BaseModel):
    """Request to rollback a slide to a previous version."""
    session_id: str
    slide_number: int = Field(..., ge=1)
    version_index: int = Field(..., ge=0)


# Response Models
class SlideContent(BaseModel):
    """Content of a single slide."""
    slide_number: int
    title: str
    content: List[str]
    speaker_notes: Optional[str] = None


class SlideVersion(BaseModel):
    """A version of a slide."""
    version: int
    title: str
    content: List[str]
    speaker_notes: Optional[str] = None
    created_at: datetime
    instruction: Optional[str] = None  # The instruction that created this version


class SlideWithHistory(BaseModel):
    """Slide with full version history."""
    slide_number: int
    current_version: int
    versions: List[SlideVersion]
    
    @property
    def current(self) -> SlideVersion:
        return self.versions[self.current_version]


class SessionResponse(BaseModel):
    """Response when starting a session."""
    session_id: str
    template: TemplateType
    tone: ToneType
    created_at: datetime
    message: str


class GenerateResponse(BaseModel):
    """Response when generation job is queued."""
    job_id: str
    session_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str
    status: JobStatus
    progress: Optional[int] = None  # 0-100
    message: Optional[str] = None
    error: Optional[str] = None


class PreviewResponse(BaseModel):
    """Response containing presentation preview."""
    session_id: str
    topic: str
    template: TemplateType
    tone: ToneType
    slides: List[SlideWithHistory]
    total_slides: int
    last_updated: datetime


class UpdateSlideResponse(BaseModel):
    """Response after updating a slide."""
    success: bool
    slide_number: int
    updated_slide: SlideWithHistory
    message: str


class DownloadResponse(BaseModel):
    """Response with download information."""
    session_id: str
    download_url: str
    filename: str
    message: str


class AuthUserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    avatar_url: Optional[str] = None
    requests_generated: int


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class HistoryItemResponse(BaseModel):
    history_id: str
    session_id: str
    topic: Optional[str] = None
    filename: str
    slide_count: int
    created_at: datetime


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: bool = True
    message: str
    code: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message in session history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    related_slide: Optional[int] = None


class SessionData(BaseModel):
    """Complete session data structure."""
    session_id: str
    topic: Optional[str] = None
    template: TemplateType
    tone: ToneType
    slides: List[SlideWithHistory] = []
    chat_history: List[ChatMessage] = []
    context_memory: str = ""  # AI context summary
    created_at: datetime
    last_updated: datetime
    
    class Config:
        arbitrary_types_allowed = True
