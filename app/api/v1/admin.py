"""Admin API: analytics and management. Requires role=admin."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, or_, cast, String, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.tests import TESTS
from app.core.dependencies import get_db, require_roles
from app.db.models.test_result import TestResult
from app.db.models.user_synthesis import UserSynthesis
from app.db.models.user import User as UserModel
from app.db.models.email_log import EmailLog
from app.schemas.admin import (
    AdminDashboardStats,
    AdminRevenuePoint,
    AdminTestsByCategory,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserUpdate,
    AdminSubscriptionStats,
    AdminTestStatsItem,
    AdminTestsAnalyticsResponse,
    AdminAIUsageStats,
    AdminAIUsageHistoryPoint,
    AdminAIUsageResponse,
    AdminEmailStats,
    AdminEmailsResponse,
    AdminEmailLogItem,
)

get_admin_user = require_roles("admin")
router = APIRouter(prefix="/admin", tags=["admin"])


def _serialize_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat().replace("+00:00", "Z") if dt.tzinfo else dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("/analytics/dashboard", response_model=AdminDashboardStats)
async def get_dashboard(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminDashboardStats:
    """Dashboard stats: users, revenue, tests, conversion."""
    # User counts
    total_result = await db.execute(select(func.count(UserModel.id)))
    total_users = total_result.scalar() or 0
    active_result = await db.execute(select(func.count(UserModel.id)).where(UserModel.is_active))
    active_users = active_result.scalar() or 0
    premium_result = await db.execute(select(func.count(UserModel.id)).where(UserModel.is_premium))
    premium_users = premium_result.scalar() or 0
    conversion_rate = (premium_users / total_users * 100) if total_users else 0.0

    # Test counts
    tests_result = await db.execute(select(func.count(TestResult.id)))
    total_tests = tests_result.scalar() or 0
    failed_result = await db.execute(
        select(func.count(TestResult.id)).where(TestResult.status != "completed")
    )
    failed_tests = failed_result.scalar() or 0

    return AdminDashboardStats(
        total_users=total_users,
        active_users=active_users,
        premium_users=premium_users,
        total_revenue=0.0,
        monthly_revenue=0.0,
        total_tests=total_tests,
        failed_tests=failed_tests,
        conversion_rate=round(conversion_rate, 1),
    )


@router.get("/analytics/revenue", response_model=list[AdminRevenuePoint])
async def get_revenue(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[AdminRevenuePoint]:
    """Revenue by month (placeholder: no revenue table yet)."""
    months = []
    for i in range(6):
        d = datetime.utcnow() - timedelta(days=30 * (5 - i))
        months.append(AdminRevenuePoint(month=d.strftime("%b"), revenue=0.0))
    return months


@router.get("/analytics/tests-by-category", response_model=list[AdminTestsByCategory])
async def get_tests_by_category(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[AdminTestsByCategory]:
    """Test counts grouped by category."""
    by_cat: dict[str, dict[str, Any]] = {}
    for t in TESTS:
        cid = t["category_id"]
        if cid not in by_cat:
            by_cat[cid] = {"category_id": cid, "category": t["category"], "tests_count": 0, "total_taken": 0}
        by_cat[cid]["tests_count"] += 1

    r = await db.execute(
        select(TestResult.test_id, func.count(TestResult.id).label("cnt"))
        .group_by(TestResult.test_id)
    )
    for row in r.all():
        test_id, cnt = row[0], row[1]
        for t in TESTS:
            if t["id"] == test_id:
                cid = t["category_id"]
                if cid in by_cat:
                    by_cat[cid]["total_taken"] += cnt
                break

    return [AdminTestsByCategory(**v) for v in by_cat.values()]


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = None,
) -> AdminUserListResponse:
    """List users with tests taken/failed. Paginated."""
    base = select(UserModel)
    if search and search.strip():
        term = f"%{search.strip()}%"
        base = base.where(
            or_(
                UserModel.email.ilike(term),
                cast(UserModel.name, String).ilike(term),
            )
        )

    count_q = select(func.count()).select_from(base.subquery())
    total_r = await db.execute(count_q)
    total = total_r.scalar() or 0

    q = base.order_by(UserModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    users = result.scalars().all()

    # Tests taken/failed per user
    user_ids = [u.id for u in users]
    if not user_ids:
        return AdminUserListResponse(users=[], total=total)

    taken_q = select(TestResult.user_id, func.count(TestResult.id).label("taken")).where(
        TestResult.user_id.in_(user_ids)
    ).group_by(TestResult.user_id)
    taken_r = await db.execute(taken_q)
    taken_map = {row[0]: row[1] for row in taken_r.all()}

    failed_q = select(TestResult.user_id, func.count(TestResult.id).label("failed")).where(
        TestResult.user_id.in_(user_ids),
        TestResult.status != "completed",
    ).group_by(TestResult.user_id)
    failed_r = await db.execute(failed_q)
    failed_map = {row[0]: row[1] for row in failed_r.all()}

    items = []
    for u in users:
        plan = "premium" if u.is_premium else "free"
        if u.subscription_status and u.subscription_status != "free":
            plan = u.subscription_status
        items.append(AdminUserListItem(
            id=str(u.id),
            name=u.name or u.full_name,
            email=u.email,
            status="active" if u.is_active else "inactive",
            is_premium=u.is_premium,
            subscription_plan=plan,
            joined_at=_serialize_dt(u.created_at) or "",
            last_active=_serialize_dt(u.updated_at),
            tests_taken=taken_map.get(u.id, 0),
            tests_failed=failed_map.get(u.id, 0),
        ))
    return AdminUserListResponse(users=items, total=total)


@router.patch("/users/{user_id}", response_model=AdminUserListItem)
async def update_user(
    user_id: int,
    body: AdminUserUpdate,
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminUserListItem:
    """Update user (active, premium, role)."""
    r = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_premium is not None:
        user.is_premium = body.is_premium
    if body.role is not None:
        user.role = body.role
    await db.commit()
    await db.refresh(user)

    taken_r = await db.execute(select(func.count(TestResult.id)).where(TestResult.user_id == user.id))
    failed_r = await db.execute(select(func.count(TestResult.id)).where(
        TestResult.user_id == user.id, TestResult.status != "completed"
    ))
    plan = "premium" if user.is_premium else (user.subscription_status or "free")
    return AdminUserListItem(
        id=str(user.id),
        name=user.name or user.full_name,
        email=user.email,
        status="active" if user.is_active else "inactive",
        is_premium=user.is_premium,
        subscription_plan=plan,
        joined_at=_serialize_dt(user.created_at) or "",
        last_active=_serialize_dt(user.updated_at),
        tests_taken=taken_r.scalar() or 0,
        tests_failed=failed_r.scalar() or 0,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    admin_user: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a user and their related data (test results, synthesis, email logs). Cannot delete yourself."""
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    r = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.execute(delete(TestResult).where(TestResult.user_id == user_id))
    await db.execute(delete(UserSynthesis).where(UserSynthesis.user_id == user_id))
    await db.execute(delete(EmailLog).where(EmailLog.user_id == user_id))
    await db.delete(user)
    await db.commit()


@router.get("/subscriptions", response_model=AdminSubscriptionStats)
async def get_subscription_stats(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminSubscriptionStats:
    """Subscription stats and plan breakdown."""
    premium_r = await db.execute(select(func.count(UserModel.id)).where(UserModel.is_premium))
    active_subs = premium_r.scalar() or 0
    total_r = await db.execute(select(func.count(UserModel.id)))
    total = total_r.scalar() or 0
    free_r = await db.execute(select(func.count(UserModel.id)).where(UserModel.is_premium == False))
    free_users = free_r.scalar() or 0
    plan_breakdown = [
        {"name": "Free", "users": free_users, "revenue": 0.0},
        {"name": "Premium", "users": active_subs, "revenue": 0.0},
    ]
    return AdminSubscriptionStats(
        active_subscriptions=active_subs,
        mrr=0.0,
        free_users=free_users,
        churn_rate=0.0,
        plan_breakdown=plan_breakdown,
    )


@router.get("/tests", response_model=AdminTestsAnalyticsResponse)
async def get_tests_analytics(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminTestsAnalyticsResponse:
    """Tests analytics: per-test taken/completed, categories."""
    tests_by_id = {t["id"]: dict(t) for t in TESTS}
    r = await db.execute(
        select(TestResult.test_id, TestResult.status, func.count(TestResult.id).label("cnt"))
        .group_by(TestResult.test_id, TestResult.status)
    )
    agg: dict[int, dict[str, Any]] = {}
    for row in r.all():
        tid, status, cnt = row[0], row[1], row[2]
        if tid not in agg:
            agg[tid] = {"taken": 0, "completed": 0, "scores": []}
        agg[tid]["taken"] += cnt
        if status == "completed":
            agg[tid]["completed"] += cnt

    total_taken = sum(a["taken"] for a in agg.values())
    total_completed = sum(a["completed"] for a in agg.values())
    total_incomplete = total_taken - total_completed
    completion_rate = (total_completed / total_taken * 100) if total_taken else 0.0

    tests_list = []
    for t in TESTS:
        tid = t["id"]
        a = agg.get(tid, {"taken": 0, "completed": 0})
        taken = a["taken"]
        completed = a["completed"]
        cr = (completed / taken * 100) if taken else 0.0
        tests_list.append(AdminTestStatsItem(
            id=tid,
            name=t["title"],
            category_id=t["category_id"],
            category=t["category"],
            taken=taken,
            completed=completed,
            completion_rate=round(cr, 1),
            avg_score=None,
        ))

    categories = []
    seen = set()
    for t in TESTS:
        cid = t["category_id"]
        if cid not in seen:
            seen.add(cid)
            cat_tests = [x for x in TESTS if x["category_id"] == cid]
            categories.append({
                "id": cid,
                "name": t["category"],
                "color": f"hsl(var(--chart-{len(categories) + 1}))",
                "testCount": len(cat_tests),
                "totalTaken": sum(agg.get(x["id"], {}).get("taken", 0) for x in cat_tests),
            })

    return AdminTestsAnalyticsResponse(
        total_taken=total_taken,
        total_completed=total_completed,
        total_incomplete=total_incomplete,
        completion_rate=round(completion_rate, 1),
        tests=tests_list,
        categories=categories,
    )


@router.get("/ai-usage", response_model=AdminAIUsageResponse)
async def get_ai_usage(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminAIUsageResponse:
    """AI usage stats (narrations = completed test results; no token tracking yet)."""
    narrations_r = await db.execute(select(func.count(TestResult.id)).where(TestResult.status == "completed"))
    narrations = narrations_r.scalar() or 0
    stats = AdminAIUsageStats(
        total_tokens_used=0,
        total_cost=0.0,
        monthly_cost=0.0,
        narrations_generated=narrations,
        avg_tokens_per_narration=0,
        monthly_tokens=0,
    )
    history = []
    for i in range(6):
        d = datetime.utcnow() - timedelta(days=30 * (5 - i))
        history.append(AdminAIUsageHistoryPoint(
            month=d.strftime("%b"),
            tokens=0,
            cost=0.0,
            narrations=0,
        ))
    return AdminAIUsageResponse(stats=stats, history=history)


@router.get("/emails", response_model=AdminEmailsResponse)
async def get_emails(
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminEmailsResponse:
    """Email stats and recent logs (no open tracking yet)."""

    total_sent_q = await db.execute(
        select(func.count(EmailLog.id)).where(EmailLog.status == "sent")
    )
    total_failed_q = await db.execute(
        select(func.count(EmailLog.id)).where(EmailLog.status == "failed")
    )

    total_sent = total_sent_q.scalar() or 0
    total_failed = total_failed_q.scalar() or 0

    stats = AdminEmailStats(
        total_sent=total_sent,
        total_opened=0,
        avg_open_rate=0.0,
        scheduled_emails=0,
        active_schedules=0,
        individual_sent=total_sent + total_failed,
    )

    logs_q = await db.execute(
        select(EmailLog).order_by(EmailLog.created_at.desc()).limit(200)
    )
    logs = logs_q.scalars().all()

    emails = [
        AdminEmailLogItem(
            id=log.id,
            user_id=log.user_id,
            to_email=log.to_email,
            subject=log.subject,
            status=log.status,
            error_message=log.error_message,
            sent_at=log.created_at,
        )
        for log in logs
    ]

    return AdminEmailsResponse(
        stats=stats,
        schedules=[],
        emails=emails,
    )


class AdminSendEmailRequest(BaseModel):
    user_id: int
    subject: str
    body: str


@router.post("/emails/send", response_model=AdminEmailLogItem)
async def send_email(
    payload: AdminSendEmailRequest,
    _: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> AdminEmailLogItem:
    """Send a one-off email to a single user and log the result."""
    from app.core.email import send_email_sync, is_email_configured

    user = await db.get(UserModel, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not is_email_configured():
        raise HTTPException(
            status_code=400,
            detail="SMTP is not configured on the server.",
        )

    log = EmailLog(
        user_id=user.id,
        to_email=user.email,
        subject=payload.subject.strip(),
        body=payload.body,
        status="pending",
    )
    db.add(log)
    await db.flush()

    try:
        # Send synchronously; for higher volume we could offload to a background worker.
        send_email_sync(user.email, payload.subject.strip(), payload.body)
        log.status = "sent"
        log.error_message = None
    except Exception as exc:  # noqa: BLE001
        log.status = "failed"
        log.error_message = str(exc)

    await db.commit()
    await db.refresh(log)

    return AdminEmailLogItem(
        id=log.id,
        user_id=log.user_id,
        to_email=log.to_email,
        subject=log.subject,
        status=log.status,
        error_message=log.error_message,
        sent_at=log.created_at,
    )
