from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")


class AgentSummary(BaseModel):
    name: str
    role: str


class TaskSummary(BaseModel):
    id: str
    title: str
    status: str
