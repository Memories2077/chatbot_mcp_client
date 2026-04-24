"""
Feedback Data Models

Pydantic schemas for feedback-related operations.
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class FeedbackEntry(BaseModel):
    """Individual feedback entry stored in MongoDB."""
    feedbackId: str = Field(default_factory=lambda: datetime.now().isoformat())
    feedbackType: Literal['like', 'dislike']
    feedbackText: Optional[str] = Field(None, max_length=1000)
    userId: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FeedbackRequest(BaseModel):
    """Request schema for POST /api/feedback."""
    messageId: str = Field(..., min_length=1, max_length=200)
    serverId: Optional[str] = Field(None, min_length=1, max_length=200)  # NEW: associate with MCP server
    type: Literal['like', 'dislike']
    userId: Optional[str] = Field(None, min_length=1, max_length=100)
    comment: Optional[str] = Field(None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Response schema for feedback submission."""
    success: bool
    messageId: str
    likeCount: int
    dislikeCount: int
    totalFeedbacks: int


class LogDocument(BaseModel):
    """Extended log document schema with feedback fields."""
    messageId: str
    content: str
    role: str
    timestamp: datetime = Field(default_factory=datetime.now)

    # MCP server association (optional - feedback may be general or server-specific)
    serverId: Optional[str] = None

    # Feedback fields
    likeCount: int = 0
    dislikeCount: int = 0
    feedbacks: list[FeedbackEntry] = []

    class Config:
        extra = "allow"  # Allow other existing fields
