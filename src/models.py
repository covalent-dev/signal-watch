"""Pydantic models and SQLAlchemy ORM models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


# SQLAlchemy Base
class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# SQLAlchemy ORM Models
class ChannelORM(Base):
    """YouTube channel database model."""
    __tablename__ = "channels"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    domain = Column(String, default="ai")
    active = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    videos = relationship("VideoORM", back_populates="channel")


class VideoORM(Base):
    """YouTube video database model."""
    __tablename__ = "videos"

    id = Column(String, primary_key=True)
    channel_id = Column(String, ForeignKey("channels.id"), nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    channel = relationship("ChannelORM", back_populates="videos")
    transcript = relationship("TranscriptORM", back_populates="video", uselist=False)
    summaries = relationship("SummaryORM", back_populates="video")


class TranscriptORM(Base):
    """Video transcript database model."""
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False, unique=True)
    source = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    language = Column(String, default="en")
    fetched_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("VideoORM", back_populates="transcript")


class SummaryORM(Base):
    """LLM-generated summary database model."""
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    model = Column(String, nullable=False)
    summary_text = Column(Text, nullable=False)
    key_points = Column(Text, nullable=True)  # JSON array
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("VideoORM", back_populates="summaries")


class RunORM(Base):
    """Pipeline execution log database model."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    new_videos = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    runtime_seconds = Column(Float, nullable=True)
    status = Column(String, default="running")


# Pydantic Models for API
class ChannelCreate(BaseModel):
    """Schema for creating a channel."""
    id: str
    name: str
    url: str = ""
    domain: str = "ai"
    priority: int = 10


class ChannelResponse(BaseModel):
    """Schema for channel response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    url: str
    domain: str
    active: bool
    last_checked_at: Optional[datetime] = None
    created_at: datetime


class VideoResponse(BaseModel):
    """Schema for video response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    title: str
    url: str
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str
    created_at: datetime
    channel_name: Optional[str] = None


class VideoDetailResponse(BaseModel):
    """Schema for detailed video response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    title: str
    url: str
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str
    created_at: datetime
    channel_name: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[list[str]] = None
    category: Optional[str] = None


class TranscriptResponse(BaseModel):
    """Schema for transcript response."""
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    source: Optional[str] = None
    text: str
    language: str
    fetched_at: datetime


class DigestVideo(BaseModel):
    """Video entry in a digest."""
    title: str
    link: str
    channel: str
    published: Optional[datetime] = None
    summary: str
    key_points: list[str] = []
    category: str = "ai"


class DigestResponse(BaseModel):
    """Schema for digest response."""
    source: str = "signal-watch"
    generated_at: datetime
    date: str
    videos: list[DigestVideo] = []


class RunResponse(BaseModel):
    """Schema for run response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    new_videos: int
    processed: int
    errors: int
    runtime_seconds: Optional[float] = None
    status: str


class StatsResponse(BaseModel):
    """Schema for statistics response."""
    total_channels: int
    active_channels: int
    total_videos: int
    processed_videos: int
    pending_videos: int
    failed_videos: int
    total_transcripts: int
    total_summaries: int
    last_run: Optional[RunResponse] = None


class PollResponse(BaseModel):
    """Schema for poll response."""
    status: str
    new_videos: int
    processed: int
    errors: int
    run_id: int


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    database: str
    ollama: str
