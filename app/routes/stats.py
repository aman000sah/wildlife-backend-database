from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models.report import Report, ConditionEnum, StatusEnum
from app.models.alert import Alert, AlertStatusEnum
from app.models.ml_detection import MLDetection

router = APIRouter()


# ── GET /api/stats/public ─────────────────────────────────────────────────────
# Matches Flutter's ApiService.getPublicStats(). Intentionally has NO auth
# dependency — this is the community-wide summary shown to any user,
# including on screens reached before/without a verified admin session.
@router.get("/public")
def get_public_stats(db: Session = Depends(get_db)):
    total_reports = db.query(Report).count()

    verified_total = db.query(Report).filter(
        Report.status == StatusEnum.verified
    ).count()

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    reports_this_week = db.query(Report).filter(
        Report.timestamp >= week_ago
    ).count()

    return {
        "total_reports": total_reports,
        "verified_total": verified_total,
        "reports_this_week": reports_this_week,
    }


# ── GET /api/stats/summary ────────────────────────────────────────────────────
# App-wide KPI summary for the dashboard's "Overview" section. No auth
# dependency — same reasoning as /public: this is community-wide usage
# data, visible to every user regardless of role.
#
# Definitions (confirmed with product owner):
#   - condition breakdown (normal/injured/rage/poached) counts ALL
#     submitted reports, regardless of status.
#   - "suspicious" is a separate bucket — it's a report STATUS (low ML
#     confidence on the photo), not a condition, so it's reported
#     alongside the condition breakdown rather than folded into it.
#   - "incidents resolved" = Alerts an admin has clicked Resolve on
#     (Alert.status == resolved), NOT verified report count.
@router.get("/summary")
def get_summary_stats(db: Session = Depends(get_db)):
    total_reports = db.query(Report).count()

    condition_counts = {
        "normal": db.query(Report).filter(Report.condition == ConditionEnum.normal).count(),
        "injured": db.query(Report).filter(Report.condition == ConditionEnum.injured).count(),
        "rage": db.query(Report).filter(Report.condition == ConditionEnum.rage).count(),
        "poached": db.query(Report).filter(Report.condition == ConditionEnum.poached).count(),
    }

    suspicious_count = db.query(Report).filter(
        Report.status == StatusEnum.suspicious
    ).count()

    verified_total = db.query(Report).filter(
        Report.status == StatusEnum.verified
    ).count()

    pending_total = db.query(Report).filter(
        Report.status == StatusEnum.pending
    ).count()

    rejected_total = db.query(Report).filter(
        Report.status == StatusEnum.rejected
    ).count()

    incidents_resolved = db.query(Alert).filter(
        Alert.status == AlertStatusEnum.resolved
    ).count()

    active_alerts = db.query(Alert).filter(
        Alert.status == AlertStatusEnum.active
    ).count()

    # ── Verification Pipeline (NEW) ─────────────────────────────────────────
    # Two DISTINCT stages, not slices of one pie:
    #   1) AI Detection — only meaningful for reports submitted WITH a photo
    #      (MLDetection rows only exist for those). is_verified here means
    #      "the model's confidence cleared the threshold", nothing more.
    #   2) Admin Decision — every report's actual moderation outcome,
    #      independent of what the AI thought (an admin can verify a
    #      report the AI flagged, or reject one the AI was confident about).
    ai_verified_count = db.query(MLDetection).filter(
        MLDetection.is_verified == True  # noqa: E712
    ).count()
    ai_flagged_count = db.query(MLDetection).filter(
        MLDetection.is_verified == False  # noqa: E712
    ).count()

    # ── Species breakdown (FIXED) ────────────────────────────────────────────
    # Groups by species_reported across ALL submitted reports — this is
    # the final, authoritative species name on every report (submit_report
    # overwrites it with the ML detection result whenever a photo is
    # analyzed), so no join to ml_detections is needed here.
    #
    # Two real-world issues this query corrects for:
    #   1) The SAME animal can be stored with different casing depending
    #      on submission path (e.g. "wolf" from a no-photo/dropdown
    #      report vs "Wolf" from an ML-detected one). Postgres GROUP BY
    #      is case-sensitive, so without normalizing, these silently
    #      split into separate rows. We group by func.lower(...) instead,
    #      then pick one display name per group (the most common casing,
    #      falling back to title case if there's a tie).
    #   2) Reports with no usable species name (NULL, empty, or the
    #      literal value "unknown") are excluded entirely rather than
    #      shown as an "Unknown" bucket — that's not an animal sighting.
    species_rows = (
        db.query(
            func.lower(Report.species_reported).label("species_key"),
            Report.species_reported,
            func.count(Report.report_id),
        )
        .filter(Report.species_reported.isnot(None))
        .filter(func.trim(Report.species_reported) != "")
        .filter(func.lower(Report.species_reported) != "unknown")
        .group_by(func.lower(Report.species_reported), Report.species_reported)
        .all()
    )

    # Merge casing variants of the same species_key in Python, keeping
    # whichever exact-cased spelling appeared most often as the display name.
    merged: dict[str, dict] = {}
    for species_key, raw_name, count in species_rows:
        entry = merged.setdefault(species_key, {"count": 0, "name_counts": {}})
        entry["count"] += count
        entry["name_counts"][raw_name] = entry["name_counts"].get(raw_name, 0) + count

    species_breakdown = []
    for species_key, entry in merged.items():
        # Pick the most-used exact spelling; ties broken alphabetically
        # for a stable, deterministic display name.
        display_name = max(entry["name_counts"].items(), key=lambda kv: (kv[1], kv[0]))[0]
        species_breakdown.append({"species": display_name, "count": entry["count"]})

    species_breakdown.sort(key=lambda row: (-row["count"], row["species"].lower()))

    return {
        "total_reports": total_reports,
        "condition_breakdown": condition_counts,
        "species_breakdown": species_breakdown,
        "suspicious_total": suspicious_count,
        "verified_total": verified_total,
        "pending_total": pending_total,
        "rejected_total": rejected_total,
        "incidents_resolved": incidents_resolved,
        "active_alerts": active_alerts,
        # AI Detection donut (left)
        "ai_verified_total": ai_verified_count,
        "ai_flagged_total": ai_flagged_count,
        # Admin Decision donut (right) reuses verified_total/rejected_total/
        # pending_total above — no need to duplicate those.
    }

