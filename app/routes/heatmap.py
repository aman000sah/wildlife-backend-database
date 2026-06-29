from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.report import ConditionEnum

router = APIRouter()

CONDITION_SEVERITY = {
    ConditionEnum.normal.value: 0,
    ConditionEnum.injured.value: 1,
    ConditionEnum.poached.value: 2,
    ConditionEnum.rage.value: 3,
}

DEFAULT_CLUSTER_RADIUS_METERS = 750
MIN_CLUSTER_RADIUS_METERS = 50
MAX_CLUSTER_RADIUS_METERS = 20000


class TimeRange(str, Enum):
    last_24h = "24h"
    last_7d = "7d"
    last_30d = "30d"
    all_time = "all"


def _time_range_to_start(time_range: TimeRange) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    if time_range == TimeRange.last_24h:
        return now - timedelta(hours=24)
    if time_range == TimeRange.last_7d:
        return now - timedelta(days=7)
    if time_range == TimeRange.last_30d:
        return now - timedelta(days=30)
    return None


@router.get("")
def get_heatmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    range: TimeRange = Query(
        TimeRange.last_7d,
        description="Time window: 24h, 7d, 30d, or all",
    ),
    cluster_radius_meters: int = Query(
        DEFAULT_CLUSTER_RADIUS_METERS,
        ge=MIN_CLUSTER_RADIUS_METERS,
        le=MAX_CLUSTER_RADIUS_METERS,
        description="DBSCAN cluster radius in meters",
    ),
    condition: Optional[ConditionEnum] = Query(
        None, description="Optional filter to a single condition"
    ),
):
    """
    Clustered wildlife-report hotspots for the heatmap and marker view.

    ✅ ACCESS RULE: the heatmap shows VERIFIED reports only, for every
    user (admin or regular). Approved reports create alerts and heatmap
    markers, while pending, suspicious, and rejected reports never appear
    here for anyone.
    """
    start_time = _time_range_to_start(range)

    where_clauses = [
        "latitude IS NOT NULL",
        "longitude IS NOT NULL",
        "status = 'verified'",

    ]
    params: dict = {}

    if start_time is not None:
        where_clauses.append("timestamp >= :start_time")
        params["start_time"] = start_time

    if condition is not None:
        where_clauses.append("condition = :condition")
        params["condition"] = condition.value

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        WITH clustered AS (
            SELECT
                report_id,
                latitude,
                longitude,
                condition,
                timestamp,
                ST_ClusterDBSCAN(
                    ST_Transform(
                        ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                        3857
                    ),
                    {cluster_radius_meters},
                    1
                ) OVER () AS cluster_id
            FROM reports
            WHERE {where_sql}
        ),
        per_condition AS (
            SELECT
                cluster_id,
                condition,
                COUNT(*) AS condition_count,
                SUM(latitude)  AS lat_sum,
                SUM(longitude) AS lng_sum,
                MAX(timestamp) AS max_timestamp
            FROM clustered
            GROUP BY cluster_id, condition
        )
        SELECT
            cluster_id,
            SUM(condition_count)                         AS total_count,
            SUM(lat_sum)  / SUM(condition_count)         AS centroid_lat,
            SUM(lng_sum)  / SUM(condition_count)         AS centroid_lng,
            MAX(max_timestamp)                           AS last_reported_at,
            jsonb_object_agg(condition, condition_count)  AS breakdown
        FROM per_condition
        GROUP BY cluster_id
        ORDER BY total_count DESC;
    """)

    rows = db.execute(query, params).fetchall()

    points = []
    total_reports = 0

    for row in rows:
        breakdown: dict = dict(row.breakdown)
        total_count = int(row.total_count)
        total_reports += total_count

        dominant = max(
            breakdown.keys(),
            key=lambda c: CONDITION_SEVERITY.get(c, -1),
        )

        points.append({
            "latitude": float(row.centroid_lat),
            "longitude": float(row.centroid_lng),
            "count": total_count,
            "dominant_condition": dominant,
            "conditions_breakdown": breakdown,
            "last_reported_at": row.last_reported_at.isoformat()
                if row.last_reported_at else None,
        })

    return {
        "range": range.value,
        "cluster_radius_meters": cluster_radius_meters,
        "total_reports": total_reports,
        "points": points,
    }


@router.get("/trend")
def get_heatmap_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    range: TimeRange = Query(
        TimeRange.last_30d,
        description="Time window to bucket by day: 24h, 7d, 30d, or all",
    ),
):
    """
    Daily report-count trend with condition breakdown.
    Same access rule as get_heatmap: VERIFIED reports only, always,
    for every user, independent of broadcast state.
    """
    start_time = _time_range_to_start(range)

    where_clauses = [
        "latitude IS NOT NULL",
        "longitude IS NOT NULL",
        "status = 'verified'",
    ]
    params: dict = {}

    if start_time is not None:
        where_clauses.append("timestamp >= :start_time")
        params["start_time"] = start_time

    where_sql = " AND ".join(where_clauses)

    query = text(f"""
        SELECT
            DATE_TRUNC('day', timestamp)::date AS day,
            condition,
            COUNT(*) AS condition_count
        FROM reports
        WHERE {where_sql}
        GROUP BY day, condition
        ORDER BY day ASC;
    """)

    rows = db.execute(query, params).fetchall()

    buckets_by_day: dict = {}
    for row in rows:
        day_str = row.day.isoformat()
        buckets_by_day.setdefault(day_str, {})
        buckets_by_day[day_str][row.condition] = int(row.condition_count)

    buckets = [
        {
            "date": day_str,
            "count": sum(breakdown.values()),
            "conditions_breakdown": breakdown,
        }
        for day_str, breakdown in sorted(buckets_by_day.items())
    ]

    return {"range": range.value, "buckets": buckets}