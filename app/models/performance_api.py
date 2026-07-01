"""Performance admin API response models (frontend TS parity)."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PerformanceRefreshViewsResponse(BaseModel):
    success: bool
    message: str


class PerformanceSlowQueryRow(BaseModel):
    query: str = ""
    calls: int = 0
    mean_exec_time_ms: float = 0.0
    max_exec_time_ms: float = 0.0


class PerformanceQueryAnalysisResponse(BaseModel):
    slow_queries: List[PerformanceSlowQueryRow] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    pg_stat_statements_available: bool = False
    raw: Dict[str, Any] = Field(default_factory=dict)


class PerformanceCacheClearResponse(BaseModel):
    success: bool
    pattern: str
    deleted_count: int
