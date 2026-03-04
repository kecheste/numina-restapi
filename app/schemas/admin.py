"""Admin API response schemas for analytics and management."""

from datetime import datetime

from pydantic import BaseModel, Field


class AdminDashboardStats(BaseModel):
    total_users: int = 0
    active_users: int = 0
    premium_users: int = 0
    total_revenue: float = 0.0
    monthly_revenue: float = 0.0
    total_tests: int = 0
    failed_tests: int = 0
    conversion_rate: float = 0.0


class AdminRevenuePoint(BaseModel):
    month: str
    revenue: float


class AdminTestsByCategory(BaseModel):
    category_id: str
    category: str
    tests_count: int
    total_taken: int


class AdminUserListItem(BaseModel):
    id: str
    name: str | None
    email: str
    status: str
    is_premium: bool
    subscription_plan: str
    joined_at: str
    last_active: str | None
    tests_taken: int = 0
    tests_failed: int = 0


class AdminUserListResponse(BaseModel):
    users: list[AdminUserListItem]
    total: int


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_premium: bool | None = None
    role: str | None = None


class AdminSubscriptionStats(BaseModel):
    active_subscriptions: int = 0
    mrr: float = 0.0
    free_users: int = 0
    churn_rate: float = 0.0
    plan_breakdown: list[dict] = Field(default_factory=list)


class AdminTestStatsItem(BaseModel):
    id: int
    name: str
    category_id: str
    category: str
    taken: int = 0
    completed: int = 0
    completion_rate: float = 0.0
    avg_score: float | None = None


class AdminTestsAnalyticsResponse(BaseModel):
    total_taken: int = 0
    total_completed: int = 0
    total_incomplete: int = 0
    completion_rate: float = 0.0
    tests: list[AdminTestStatsItem] = Field(default_factory=list)
    categories: list[dict] = Field(default_factory=list)


class AdminAIUsageStats(BaseModel):
    total_tokens_used: int = 0
    total_cost: float = 0.0
    monthly_cost: float = 0.0
    narrations_generated: int = 0
    avg_tokens_per_narration: int = 0
    monthly_tokens: int = 0


class AdminAIUsageHistoryPoint(BaseModel):
    month: str
    tokens: int = 0
    cost: float = 0.0
    narrations: int = 0


class AdminAIUsageResponse(BaseModel):
    stats: AdminAIUsageStats
    history: list[AdminAIUsageHistoryPoint] = Field(default_factory=list)


class AdminEmailStats(BaseModel):
    total_sent: int = 0
    total_opened: int = 0
    avg_open_rate: float = 0.0
    scheduled_emails: int = 0
    active_schedules: int = 0
    individual_sent: int = 0


class AdminScheduledEmail(BaseModel):
    id: str
    name: str
    schedule: str
    audience: str
    last_sent: str | None
    status: str
    sent_count: int = 0
    open_rate: float = 0.0


class AdminEmailLogItem(BaseModel):
    id: int
    user_id: int | None = None
    to_email: str
    subject: str
    status: str
    error_message: str | None = None
    sent_at: datetime


class AdminEmailsResponse(BaseModel):
    stats: AdminEmailStats
    schedules: list[AdminScheduledEmail] = Field(default_factory=list)
    emails: list[AdminEmailLogItem] = Field(default_factory=list)
