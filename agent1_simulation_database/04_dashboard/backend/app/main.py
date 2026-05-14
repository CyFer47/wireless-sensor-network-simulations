from pathlib import Path
import csv
import io
import logging
from typing import Any, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.db import run_db_check, REQUIRED_TABLES
from app.repository import MonitorRepository
from app.serializers import rows_to_jsonable, to_jsonable
from app.settings import settings

repo = MonitorRepository()
logger = logging.getLogger("wsn_web_monitor")

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

env_path = Path(__file__).resolve().parents[1] / "config" / ".env"
logger.info(
    "Backend settings loaded: web_host=%s web_port=%s | DB connection: host=%s port=%s db=%s user=%s schema=%s timeout=%ds sslmode=%s password=%s",
    settings.app_host,
    settings.app_port,
    settings.pg_host,
    settings.pg_port,
    settings.pg_database,
    settings.pg_user,
    settings.pg_schema,
    settings.pg_connect_timeout,
    settings.pg_sslmode,
    "set" if settings.pg_password else "MISSING",
)
logger.info("Env file: %s (exists=%s)", str(env_path), env_path.exists())

app = FastAPI(
    title="WSN Web DB Monitor",
    version="0.4.1-m4a",
    description="Milestone 4A table observer and run inspection backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_db_diagnostics() -> None:
    check = run_db_check()
    connected = (
        check["tcp_connection"]
        and check["authentication"]
        and check["schema_exists"]
        and len(check["required_tables"]["missing"]) == 0
    )
    if connected:
        logger.info(
            "DB check: ✓ CONNECTED | schema=%s | tables: %d/%d present",
            settings.pg_schema,
            check["required_tables"]["present_count"],
            len(REQUIRED_TABLES),
        )
    else:
        if not check["tcp_connection"]:
            logger.error(
                "DB check: ✗ TCP UNREACHABLE | %s | %s@%s:%s | error_type=%s | error=%s",
                settings.pg_database,
                settings.pg_user,
                settings.pg_host,
                settings.pg_port,
                check["error_type"],
                check["error"],
            )
        elif not check["authentication"]:
            logger.error(
                "DB check: ✗ AUTHENTICATION FAILED | %s | %s@%s | error=%s",
                settings.pg_database,
                settings.pg_user,
                settings.pg_host,
                check["error"],
            )
        elif not check["schema_exists"]:
            logger.error(
                "DB check: ✗ SCHEMA NOT FOUND | schema=%s does not exist in %s | user=%s",
                settings.pg_schema,
                settings.pg_database,
                settings.pg_user,
            )
        elif check["required_tables"]["missing"]:
            logger.error(
                "DB check: ✗ MISSING TABLES | %d missing in schema %s: %s",
                len(check["required_tables"]["missing"]),
                settings.pg_schema,
                ", ".join(check["required_tables"]["missing"]),
            )


@app.exception_handler(psycopg2.OperationalError)
def handle_db_error(_: Request, exc: psycopg2.OperationalError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "database_unavailable",
            "detail": str(exc).splitlines()[0],
        },
    )


@app.get("/api/health")
def health() -> dict:
    check = run_db_check()
    connected = (
        check["tcp_connection"]
        and check["authentication"]
        and check["schema_exists"]
        and len(check["required_tables"]["missing"]) == 0
    )
    if not connected:
        logger.error(
            "DB health check failed: type=%s error=%s schema_exists=%s missing_tables=%s",
            check["error_type"],
            check["error"],
            check["schema_exists"],
            check["required_tables"]["missing"],
        )

    return {
        "service": "wsn-web-monitor",
        "status": "ok",
        "database": "connected" if connected else "disconnected",
        "auto_refresh_seconds": settings.auto_refresh_seconds,
    }


@app.get("/api/debug/db-check")
def debug_db_check() -> dict:
    check = run_db_check()
    connected = (
        check["tcp_connection"]
        and check["authentication"]
        and check["schema_exists"]
        and len(check["required_tables"]["missing"]) == 0
    )
    check["database"] = "connected" if connected else "disconnected"
    return check


@app.get("/api/runs")
def runs(
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("run_id"),
    order: str = Query("desc"),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    data = repo.list_runs(page=page, size=safe_size, sort=sort, order=order)
    data["items"] = rows_to_jsonable(data["items"])
    return data


@app.get("/api/runs/latest")
def latest_run() -> dict:
    row = repo.latest_run()
    if row is None:
        raise HTTPException(status_code=404, detail="no runs available")
    return to_jsonable(row)


@app.get("/api/runs/{run_id}/overview")
def overview(run_id: int) -> dict:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    return to_jsonable(repo.get_overview(run_id))


@app.get("/api/runs/{run_id}/counts")
def counts(run_id: int) -> dict:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    return to_jsonable(repo.get_counts(run_id))


@app.get("/api/runs/{run_id}/nodes-static")
def nodes_static(
    run_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("node_id"),
    order: str = Query("asc"),
    nodeId: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    clusterId: Optional[int] = Query(None),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    data = repo.get_nodes_static(run_id, page, safe_size, sort, order, nodeId, role, clusterId)
    data["items"] = rows_to_jsonable(data["items"])
    return data


@app.get("/api/runs/{run_id}/global-timeseries")
def global_timeseries(
    run_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("sim_time_s"),
    order: str = Query("asc"),
    startTime: Optional[float] = Query(None),
    endTime: Optional[float] = Query(None),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    data = repo.get_global_timeseries(run_id, page, safe_size, sort, order, startTime, endTime)
    data["items"] = rows_to_jsonable(data["items"])
    return data


@app.get("/api/runs/{run_id}/latest-global")
def latest_global(run_id: int) -> dict:
    row = repo.latest_global(run_id)
    return {"item": to_jsonable(row) if row else None}


@app.get("/api/runs/{run_id}/cluster-timeseries")
def cluster_timeseries(
    run_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("sim_time_s"),
    order: str = Query("asc"),
    clusterId: Optional[int] = Query(None),
    startTime: Optional[float] = Query(None),
    endTime: Optional[float] = Query(None),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    data = repo.get_cluster_timeseries(run_id, page, safe_size, sort, order, startTime, endTime, clusterId)
    data["items"] = rows_to_jsonable(data["items"])
    return data


@app.get("/api/runs/{run_id}/latest-clusters")
def latest_clusters(run_id: int) -> dict:
    items = repo.latest_clusters(run_id)
    return {"count": len(items), "items": rows_to_jsonable(items)}


@app.get("/api/runs/{run_id}/events")
def events(
    run_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("sim_time_s"),
    order: str = Query("desc"),
    eventType: Optional[str] = Query(None),
    startTime: Optional[float] = Query(None),
    endTime: Optional[float] = Query(None),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    data = repo.get_events(run_id, page, safe_size, sort, order, eventType, startTime, endTime)
    data["items"] = rows_to_jsonable(data["items"])
    return data


@app.get("/api/runs/{run_id}/latest-events")
def latest_events(run_id: int, limit: int = Query(20, ge=1, le=200)) -> dict:
    items = repo.latest_events(run_id, limit)
    return {"count": len(items), "items": rows_to_jsonable(items)}


@app.get("/api/runs/{run_id}/run-summary")
def run_summary(run_id: int) -> dict:
    row = repo.get_run_summary(run_id)
    return {"item": to_jsonable(row) if row else None}


@app.get("/api/runs/{run_id}/node-final-summary")
def node_final_summary(
    run_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("residual_j"),
    order: str = Query("asc"),
    role: Optional[str] = Query(None),
    clusterId: Optional[int] = Query(None),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    data = repo.get_node_final_summary(run_id, page, safe_size, sort, order, role, clusterId)
    data["items"] = rows_to_jsonable(data["items"])
    data["top_lowest_residual"] = rows_to_jsonable(data.get("top_lowest_residual", []))
    return data


@app.get("/api/raw/table")
def raw_table(
    table: str,
    runId: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("run_id"),
    order: str = Query("desc"),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    try:
        data = repo.get_raw_table(runId, table, page, safe_size, sort, order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    data["items"] = rows_to_jsonable(data["items"])
    return data


@app.get("/api/raw/tables")
def raw_tables() -> dict:
    return {"tables": sorted(list(repo.allowed_tables.keys()))}


@app.get("/api/run/{run_id}/overview")
def run_overview_v2(run_id: int) -> dict:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    return to_jsonable(repo.get_run_overview_v2(run_id))


@app.get("/api/run/{run_id}/global-timeseries")
def run_global_timeseries_v2(
    run_id: int,
    from_time: Optional[float] = Query(None),
    to_time: Optional[float] = Query(None),
) -> list[dict]:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    items = repo.get_global_timeseries_inspection(run_id, from_time, to_time)
    return rows_to_jsonable(items)


@app.get("/api/run/{run_id}/cluster-timeseries")
def run_cluster_timeseries_v2(
    run_id: int,
    cluster_id: Optional[int] = Query(None),
    from_time: Optional[float] = Query(None),
    to_time: Optional[float] = Query(None),
) -> list[dict]:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    items = repo.get_cluster_timeseries_inspection(run_id, cluster_id, from_time, to_time)
    return rows_to_jsonable(items)


@app.get("/api/run/{run_id}/events")
def run_events_v2(
    run_id: int,
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    from_time: Optional[float] = Query(None),
    to_time: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("sim_time_s"),
    order: str = Query("desc"),
) -> dict:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    safe_size = min(size, settings.max_page_size)
    data = repo.get_events_inspection(run_id, search, category, from_time, to_time, page, safe_size, sort, order)
    data["items"] = rows_to_jsonable(data["items"])
    return data


@app.get("/api/run/{run_id}/node-final-summary")
def run_node_final_v2(
    run_id: int,
    cluster_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    sort: str = Query("residual_j"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
) -> dict:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    safe_size = min(size, settings.max_page_size)
    data = repo.get_node_final_summary_inspection(run_id, cluster_id, role, sort, order, page, safe_size)
    data["items"] = rows_to_jsonable(data["items"])
    data["top_lowest_residual"] = rows_to_jsonable(data.get("top_lowest_residual", []))
    data["top_highest_consumed"] = rows_to_jsonable(data.get("top_highest_consumed", []))
    data["role_summary"] = rows_to_jsonable(data.get("role_summary", []))
    return data


@app.get("/api/run/{run_id}/replay-snapshot")
def run_replay_snapshot(
    run_id: int,
    time: float = Query(..., description="Requested simulation time"),
    window: float = Query(1.0, ge=0.0, le=30.0),
) -> dict:
    if not repo.run_exists(run_id):
        raise HTTPException(status_code=404, detail=f"run_id {run_id} not found")
    data = repo.get_replay_snapshot(run_id, time, window)
    data["global"] = to_jsonable(data.get("global")) if data.get("global") else None
    data["clusters"] = rows_to_jsonable(data.get("clusters", []))
    data["events"] = rows_to_jsonable(data.get("events", []))
    return to_jsonable(data)


def _parse_bool_str(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    low = value.strip().lower()
    if low in {"1", "true", "yes", "y", "on"}:
        return True
    if low in {"0", "false", "no", "n", "off"}:
        return False
    raise HTTPException(status_code=400, detail=f"invalid boolean value: {value}")


def _parse_run_ids_csv(selected_run_ids: Optional[str]) -> list[int]:
    if not selected_run_ids:
        return []
    out: list[int] = []
    for raw in selected_run_ids.split(","):
        s = raw.strip()
        if not s:
            continue
        try:
            out.append(int(s))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"invalid run id: {s}") from exc
    return sorted(list(set(out)))


def _build_analytics_filters(
    experiment_version: Optional[str],
    scenario_name: Optional[str],
    recovery_enabled: Optional[str],
    failure_time_s: Optional[float],
    recovery_delay_s: Optional[float],
    sim_time_s: Optional[float],
    node_count: Optional[int],
    cluster_count: Optional[int],
    started_from: Optional[str],
    started_to: Optional[str],
    selected_run_ids: Optional[str],
) -> dict[str, Any]:
    return {
        "experiment_version": experiment_version,
        "scenario_name": scenario_name,
        "recovery_enabled": _parse_bool_str(recovery_enabled),
        "failure_time_s": failure_time_s,
        "recovery_delay_s": recovery_delay_s,
        "sim_time_s": sim_time_s,
        "node_count": node_count,
        "cluster_count": cluster_count,
        "started_from": started_from,
        "started_to": started_to,
        "run_ids": _parse_run_ids_csv(selected_run_ids),
    }


def _csv_response(filename: str, rows: list[dict[str, Any]], columns: list[str]) -> Response:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/analytics/runs")
def analytics_runs(
    page: int = Query(1, ge=1),
    size: int = Query(settings.default_page_size, ge=1),
    sort: str = Query("newest"),
    order: str = Query("desc"),
    experiment_version: Optional[str] = Query(None),
    scenario_name: Optional[str] = Query(None),
    recovery_enabled: Optional[str] = Query(None),
    failure_time_s: Optional[float] = Query(None),
    recovery_delay_s: Optional[float] = Query(None),
    sim_time_s: Optional[float] = Query(None),
    node_count: Optional[int] = Query(None),
    cluster_count: Optional[int] = Query(None),
    started_from: Optional[str] = Query(None),
    started_to: Optional[str] = Query(None),
    selected_run_ids: Optional[str] = Query(None),
) -> dict:
    safe_size = min(size, settings.max_page_size)
    filters = _build_analytics_filters(
        experiment_version,
        scenario_name,
        recovery_enabled,
        failure_time_s,
        recovery_delay_s,
        sim_time_s,
        node_count,
        cluster_count,
        started_from,
        started_to,
        selected_run_ids,
    )
    data = repo.get_analytics_runs(page=page, size=safe_size, sort=sort, order=order, filters=filters)
    data["items"] = rows_to_jsonable(data["items"])
    return to_jsonable(data)


@app.get("/api/analytics/summary")
def analytics_summary(
    experiment_version: Optional[str] = Query(None),
    scenario_name: Optional[str] = Query(None),
    recovery_enabled: Optional[str] = Query(None),
    failure_time_s: Optional[float] = Query(None),
    recovery_delay_s: Optional[float] = Query(None),
    sim_time_s: Optional[float] = Query(None),
    node_count: Optional[int] = Query(None),
    cluster_count: Optional[int] = Query(None),
    started_from: Optional[str] = Query(None),
    started_to: Optional[str] = Query(None),
    selected_run_ids: Optional[str] = Query(None),
) -> dict:
    filters = _build_analytics_filters(
        experiment_version,
        scenario_name,
        recovery_enabled,
        failure_time_s,
        recovery_delay_s,
        sim_time_s,
        node_count,
        cluster_count,
        started_from,
        started_to,
        selected_run_ids,
    )
    return to_jsonable(repo.get_analytics_summary(filters))


@app.get("/api/analytics/charts")
def analytics_charts(
    group_by: Optional[str] = Query(None),
    experiment_version: Optional[str] = Query(None),
    scenario_name: Optional[str] = Query(None),
    recovery_enabled: Optional[str] = Query(None),
    failure_time_s: Optional[float] = Query(None),
    recovery_delay_s: Optional[float] = Query(None),
    sim_time_s: Optional[float] = Query(None),
    node_count: Optional[int] = Query(None),
    cluster_count: Optional[int] = Query(None),
    started_from: Optional[str] = Query(None),
    started_to: Optional[str] = Query(None),
    selected_run_ids: Optional[str] = Query(None),
) -> dict:
    filters = _build_analytics_filters(
        experiment_version,
        scenario_name,
        recovery_enabled,
        failure_time_s,
        recovery_delay_s,
        sim_time_s,
        node_count,
        cluster_count,
        started_from,
        started_to,
        selected_run_ids,
    )
    return to_jsonable(repo.get_analytics_charts(filters, group_by))


@app.get("/api/analytics/export/runs.csv")
def analytics_export_runs_csv(
    experiment_version: Optional[str] = Query(None),
    scenario_name: Optional[str] = Query(None),
    recovery_enabled: Optional[str] = Query(None),
    failure_time_s: Optional[float] = Query(None),
    recovery_delay_s: Optional[float] = Query(None),
    sim_time_s: Optional[float] = Query(None),
    node_count: Optional[int] = Query(None),
    cluster_count: Optional[int] = Query(None),
    started_from: Optional[str] = Query(None),
    started_to: Optional[str] = Query(None),
    selected_run_ids: Optional[str] = Query(None),
) -> Response:
    filters = _build_analytics_filters(
        experiment_version,
        scenario_name,
        recovery_enabled,
        failure_time_s,
        recovery_delay_s,
        sim_time_s,
        node_count,
        cluster_count,
        started_from,
        started_to,
        selected_run_ids,
    )
    rows = repo._analytics_rows_all(filters)
    for r in rows:
        r["tags"] = "|".join(r.get("tags", []))
    cols = [
        "run_id",
        "experiment_version",
        "started_at",
        "scenario_name",
        "node_count",
        "cluster_count",
        "recovery_enabled",
        "failure_time_s",
        "recovery_delay_s",
        "sim_time_s",
        "raw_delivery_pct",
        "agg_rx_total",
        "total_consumed_j",
        "min_residual_j",
        "recovered_clusters",
        "failed_chs",
        "tags",
    ]
    return _csv_response("analytics-runs.csv", rows, cols)


@app.head("/api/analytics/export/runs.csv")
def analytics_export_runs_csv_head() -> Response:
    return Response(
        content="",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=analytics-runs.csv"},
    )


@app.get("/api/analytics/export/summary.csv")
def analytics_export_summary_csv(
    experiment_version: Optional[str] = Query(None),
    scenario_name: Optional[str] = Query(None),
    recovery_enabled: Optional[str] = Query(None),
    failure_time_s: Optional[float] = Query(None),
    recovery_delay_s: Optional[float] = Query(None),
    sim_time_s: Optional[float] = Query(None),
    node_count: Optional[int] = Query(None),
    cluster_count: Optional[int] = Query(None),
    started_from: Optional[str] = Query(None),
    started_to: Optional[str] = Query(None),
    selected_run_ids: Optional[str] = Query(None),
    group_by: Optional[str] = Query(None),
) -> Response:
    filters = _build_analytics_filters(
        experiment_version,
        scenario_name,
        recovery_enabled,
        failure_time_s,
        recovery_delay_s,
        sim_time_s,
        node_count,
        cluster_count,
        started_from,
        started_to,
        selected_run_ids,
    )
    summary = repo.get_analytics_summary(filters)
    charts = repo.get_analytics_charts(filters, group_by)

    rows: list[dict[str, Any]] = [
        {
            "section": "summary",
            "metric": "filtered_runs",
            "value": summary.get("filtered_runs", 0),
        },
        {
            "section": "summary",
            "metric": "recovery_success_rate_pct",
            "value": summary.get("recovery_success_rate_pct", 0),
        },
    ]
    for k, v in (summary.get("averages", {}) or {}).items():
        rows.append({"section": "average", "metric": k, "value": v})

    highlights = summary.get("highlights", {}) or {}
    for key, obj in highlights.items():
        if not obj:
            rows.append({"section": "highlight", "metric": key, "value": ""})
            continue
        if key == "best_energy_efficiency_run":
            rows.append({"section": "highlight", "metric": key, "value": obj.get("delivery_per_j"), "run_id": obj.get("run_id")})
        else:
            rows.append({"section": "highlight", "metric": key, "value": obj.get("value"), "run_id": obj.get("run_id")})

    for grp in charts.get("grouped", []) or []:
        rows.append(
            {
                "section": "grouped",
                "metric": f"group={grp.get('group')}",
                "value": grp.get("avg_raw_delivery_pct"),
                "run_id": grp.get("count"),
            }
        )

    return _csv_response("analytics-summary.csv", rows, ["section", "metric", "value", "run_id"])


@app.head("/api/analytics/export/summary.csv")
def analytics_export_summary_csv_head() -> Response:
    return Response(
        content="",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=analytics-summary.csv"},
    )


@app.get("/api/analytics/export/cluster-summary.csv")
def analytics_export_cluster_summary_csv(
    selected_run_ids: Optional[str] = Query(None),
) -> Response:
    run_ids = _parse_run_ids_csv(selected_run_ids)
    if not run_ids:
        return _csv_response("analytics-cluster-summary.csv", [], [
            "run_id",
            "cluster_id",
            "sim_time_s",
            "status",
            "original_ch_id",
            "current_ch_id",
            "mode",
            "next_hop",
            "members_count",
            "raw_rx_cum",
            "pending_raw",
            "agg_tx_cum",
            "relay_fwd_cum",
            "ch_res_j",
            "avg_mem_res_j",
            "cluster_consumed_j",
        ])
    rows = repo.get_analytics_cluster_final_for_runs(run_ids)
    cols = [
        "run_id",
        "cluster_id",
        "sim_time_s",
        "status",
        "original_ch_id",
        "current_ch_id",
        "mode",
        "next_hop",
        "members_count",
        "raw_rx_cum",
        "pending_raw",
        "agg_tx_cum",
        "relay_fwd_cum",
        "ch_res_j",
        "avg_mem_res_j",
        "cluster_consumed_j",
    ]
    return _csv_response("analytics-cluster-summary.csv", rows, cols)


@app.get("/api/analytics/export/selected.json")
def analytics_export_selected_json(
    experiment_version: Optional[str] = Query(None),
    scenario_name: Optional[str] = Query(None),
    recovery_enabled: Optional[str] = Query(None),
    failure_time_s: Optional[float] = Query(None),
    recovery_delay_s: Optional[float] = Query(None),
    sim_time_s: Optional[float] = Query(None),
    node_count: Optional[int] = Query(None),
    cluster_count: Optional[int] = Query(None),
    started_from: Optional[str] = Query(None),
    started_to: Optional[str] = Query(None),
    selected_run_ids: Optional[str] = Query(None),
    group_by: Optional[str] = Query(None),
) -> dict:
    filters = _build_analytics_filters(
        experiment_version,
        scenario_name,
        recovery_enabled,
        failure_time_s,
        recovery_delay_s,
        sim_time_s,
        node_count,
        cluster_count,
        started_from,
        started_to,
        selected_run_ids,
    )
    rows = repo._analytics_rows_all(filters)
    run_ids = [int(r["run_id"]) for r in rows]
    return to_jsonable(
        {
            "filters": filters,
            "selected_runs": rows,
            "summary": repo.get_analytics_summary(filters),
            "charts": repo.get_analytics_charts(filters, group_by),
            "cluster_summary": repo.get_analytics_cluster_final_for_runs(run_ids),
        }
    )


@app.head("/api/analytics/export/selected.json")
def analytics_export_selected_json_head() -> Response:
    return Response(content="", media_type="application/json")


@app.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/ui", StaticFiles(directory=str(frontend_dir), html=True), name="ui")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=settings.app_debug)
