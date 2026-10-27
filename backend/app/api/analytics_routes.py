"""Team analytics endpoints for Engineering Managers and Administrators."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.auth.models import Permission, Role
from app.auth.store import auth_store

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get(
    "/team",
    dependencies=[Depends(require_permission(Permission.VIEW_TEAM_ANALYTICS))],
)
def get_team_analytics(
    user: dict[str, Any] = Depends(require_permission(Permission.VIEW_TEAM_ANALYTICS)),
) -> dict[str, Any]:
    """Team-wide architecture health and productivity analytics.

    Available to ENGINEERING_MANAGER and ADMIN roles.
    """
    all_users = auth_store.list_users()
    active_users = [u for u in all_users if u["status"] == "active"]
    pending_users = [u for u in all_users if u["status"] == "pending"]

    # Role breakdown
    role_counts: dict[str, int] = {}
    for u in all_users:
        r = u["role"].value if isinstance(u["role"], Role) else str(u["role"])
        role_counts[r] = role_counts.get(r, 0) + 1

    # Recent activity count from audit log
    recent_audit = auth_store.get_audit_logs(limit=50)
    ingestion_count = sum(1 for a in recent_audit if "ingest" in a["action"])
    report_count = sum(1 for a in recent_audit if "report" in a["action"])

    return {
        "status": "ok",
        "team_metrics": {
            "total_members": len(all_users),
            "active_members": len(active_users),
            "pending_approvals": len(pending_users),
            "role_distribution": role_counts,
        },
        "activity_summary": {
            "recent_ingestions": ingestion_count,
            "recent_reports_generated": report_count,
            "audit_events_recorded": len(recent_audit),
        },
        "viewer_info": {
            "requested_by": user["work_email"],
            "role": user["role"].value if isinstance(user["role"], Role) else str(user["role"]),
        },
    }
