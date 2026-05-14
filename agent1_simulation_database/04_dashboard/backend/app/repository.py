from typing import Any, Optional

from app.db import get_connection, get_cursor


class MonitorRepository:
    allowed_tables = {
        "runs": {"default_sort": "run_id", "columns": None},
        "nodes_static": {"default_sort": "node_id", "columns": None},
        "global_timeseries": {"default_sort": "sim_time_s", "columns": None},
        "cluster_timeseries": {"default_sort": "sim_time_s", "columns": None},
        "events": {"default_sort": "event_id", "columns": None},
        "run_summary": {"default_sort": "run_id", "columns": None},
        "node_final_summary": {"default_sort": "node_id", "columns": None},
    }

    def check_db(self) -> bool:
        try:
            with get_connection() as conn:
                with get_cursor(conn) as cur:
                    cur.execute("SELECT 1 AS ok")
                    return cur.fetchone()["ok"] == 1
        except Exception:
            return False

    def _paged(self, query: str, count_query: str, params: list[Any], page: int, size: int) -> dict[str, Any]:
        offset = (page - 1) * size
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]

                cur.execute(query + " LIMIT %s OFFSET %s", params + [size, offset])
                rows = [dict(r) for r in cur.fetchall()]

        return {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size if size > 0 else 0,
            "items": rows,
        }

    def list_runs(self, page: int, size: int, sort: str, order: str) -> dict[str, Any]:
        sort_map = {
            "run_id": "r.run_id",
            "started_at": "r.started_at",
            "sim_time_s": "r.sim_time_s",
            "node_count": "r.node_count",
            "cluster_count": "r.cluster_count",
        }
        sort_col = sort_map.get(sort, "r.run_id")
        sort_order = "DESC" if order.lower() == "desc" else "ASC"

        base = """
        FROM runs r
        LEFT JOIN run_summary rs ON rs.run_id = r.run_id
        """
        query = f"""
        SELECT
            r.run_id,
            r.experiment_version,
            r.schema_version,
            r.started_at,
            r.sim_time_s,
            r.recovery_enabled,
            r.scenario_name,
            r.scenario_type,
            r.node_count,
            r.cluster_count,
            rs.raw_tx_cum,
            rs.raw_rx_cum,
            rs.agg_tx_cum,
            rs.agg_rx_cum,
            rs.failed_chs,
            rs.recovered_clusters,
            rs.consumed_j
        {base}
        ORDER BY {sort_col} {sort_order}
        """
        count_q = f"SELECT COUNT(*) AS total {base}"
        return self._paged(query, count_q, [], page, size)

    def latest_run(self) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT run_id, experiment_version, started_at, sim_time_s
                    FROM runs
                    ORDER BY run_id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def run_exists(self, run_id: int) -> bool:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute("SELECT 1 AS ok FROM runs WHERE run_id = %s", (run_id,))
                return cur.fetchone() is not None

    def get_overview(self, run_id: int) -> dict[str, Any]:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT
                        run_id,
                        scenario_name,
                        scenario_type,
                        started_at,
                        sim_time_s,
                        node_count,
                        cluster_count,
                        traffic_interval_s,
                        aggregation_interval_s,
                        failure_time_s,
                        recovery_delay_s,
                        recovery_enabled,
                        schema_version,
                        experiment_version,
                        notes
                    FROM runs
                    WHERE run_id = %s
                    """,
                    (run_id,),
                )
                metadata = dict(cur.fetchone() or {})

                cur.execute(
                    """
                    SELECT
                        final_sim_time_s,
                        raw_tx_cum,
                        raw_rx_cum,
                        agg_tx_cum,
                        agg_rx_cum,
                        direct_agg_rx_cum,
                        relayed_agg_rx_cum,
                        relay_fwd_cum,
                        failed_chs,
                        recovered_clusters,
                        avg_res_j,
                        min_res_j,
                        consumed_j,
                        low_nodes,
                        pending_raw_total
                    FROM run_summary
                    WHERE run_id = %s
                    """,
                    (run_id,),
                )
                summary = dict(cur.fetchone() or {})

                cur.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM nodes_static WHERE run_id = %s) AS nodes_static,
                        (SELECT COUNT(*) FROM global_timeseries WHERE run_id = %s) AS global_timeseries,
                        (SELECT COUNT(*) FROM cluster_timeseries WHERE run_id = %s) AS cluster_timeseries,
                        (SELECT COUNT(*) FROM events WHERE run_id = %s) AS events,
                        (SELECT COUNT(*) FROM run_summary WHERE run_id = %s) AS run_summary,
                        (SELECT COUNT(*) FROM node_final_summary WHERE run_id = %s) AS node_final_summary
                    """,
                    (run_id, run_id, run_id, run_id, run_id, run_id),
                )
                counts = dict(cur.fetchone() or {})

                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS total_events,
                        COUNT(*) FILTER (WHERE event_type ILIKE '%%FAIL%%') AS failure_events,
                        COUNT(*) FILTER (WHERE event_type ILIKE '%%RECOV%%') AS recovery_events,
                        COUNT(*) FILTER (WHERE event_type ILIKE '%%RELAY%%') AS relay_events,
                        COUNT(*) FILTER (WHERE message ILIKE '%%milestone%%') AS milestone_events
                    FROM events
                    WHERE run_id = %s
                    """,
                    (run_id,),
                )
                event_stats = dict(cur.fetchone() or {})

        return {
            "run_id": run_id,
            "metadata": metadata,
            "counts": counts,
            "run_summary": summary,
            "event_stats": event_stats,
            "integrity": {
                "has_run_summary": counts.get("run_summary", 0) > 0,
                "has_node_final_summary": counts.get("node_final_summary", 0) > 0,
            },
        }

    def get_counts(self, run_id: int) -> dict[str, Any]:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM nodes_static WHERE run_id = %s) AS nodes_static,
                        (SELECT COUNT(*) FROM global_timeseries WHERE run_id = %s) AS global_timeseries,
                        (SELECT COUNT(*) FROM cluster_timeseries WHERE run_id = %s) AS cluster_timeseries,
                        (SELECT COUNT(*) FROM events WHERE run_id = %s) AS events,
                        (SELECT COUNT(*) FROM run_summary WHERE run_id = %s) AS run_summary,
                        (SELECT COUNT(*) FROM node_final_summary WHERE run_id = %s) AS node_final_summary
                    """,
                    (run_id, run_id, run_id, run_id, run_id, run_id),
                )
                return dict(cur.fetchone() or {})

    def get_nodes_static(
        self,
        run_id: int,
        page: int,
        size: int,
        sort: str,
        order: str,
        node_id: Optional[int],
        role: Optional[str],
        cluster_id: Optional[int],
    ) -> dict[str, Any]:
        sort_map = {
            "node_id": "node_id",
            "role": "role",
            "original_cluster_id": "original_cluster_id",
            "initial_energy_j": "initial_energy_j",
            "x": "x",
            "y": "y",
        }
        sort_col = sort_map.get(sort, "node_id")
        sort_order = "DESC" if order.lower() == "desc" else "ASC"

        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if node_id is not None:
            where.append("node_id = %s")
            params.append(node_id)
        if role:
            where.append("role = %s")
            params.append(role)
        if cluster_id is not None:
            where.append("original_cluster_id = %s")
            params.append(cluster_id)

        where_sql = " AND ".join(where)
        query = f"SELECT * FROM nodes_static WHERE {where_sql} ORDER BY {sort_col} {sort_order}"
        count_q = f"SELECT COUNT(*) AS total FROM nodes_static WHERE {where_sql}"
        return self._paged(query, count_q, params, page, size)

    def get_global_timeseries(
        self,
        run_id: int,
        page: int,
        size: int,
        sort: str,
        order: str,
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> dict[str, Any]:
        sort_map = {
            "sim_time_s": "sim_time_s",
            "raw_tx_cum": "raw_tx_cum",
            "raw_rx_cum": "raw_rx_cum",
            "agg_tx_cum": "agg_tx_cum",
            "avg_res_j": "avg_res_j",
            "consumed_j": "consumed_j",
        }
        sort_col = sort_map.get(sort, "sim_time_s")
        sort_order = "DESC" if order.lower() == "desc" else "ASC"

        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if start_time is not None:
            where.append("sim_time_s >= %s")
            params.append(start_time)
        if end_time is not None:
            where.append("sim_time_s <= %s")
            params.append(end_time)

        where_sql = " AND ".join(where)
        query = f"SELECT * FROM global_timeseries WHERE {where_sql} ORDER BY {sort_col} {sort_order}"
        count_q = f"SELECT COUNT(*) AS total FROM global_timeseries WHERE {where_sql}"
        return self._paged(query, count_q, params, page, size)

    def latest_global(self, run_id: int) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    "SELECT * FROM global_timeseries WHERE run_id=%s ORDER BY sim_time_s DESC LIMIT 1",
                    (run_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def get_cluster_timeseries(
        self,
        run_id: int,
        page: int,
        size: int,
        sort: str,
        order: str,
        start_time: Optional[float],
        end_time: Optional[float],
        cluster_id: Optional[int],
    ) -> dict[str, Any]:
        sort_map = {
            "sim_time_s": "sim_time_s",
            "cluster_id": "cluster_id",
            "status": "status",
            "members_count": "members_count",
            "ch_res_j": "ch_res_j",
            "cluster_consumed_j": "cluster_consumed_j",
        }
        sort_col = sort_map.get(sort, "sim_time_s")
        sort_order = "DESC" if order.lower() == "desc" else "ASC"

        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if start_time is not None:
            where.append("sim_time_s >= %s")
            params.append(start_time)
        if end_time is not None:
            where.append("sim_time_s <= %s")
            params.append(end_time)
        if cluster_id is not None:
            where.append("cluster_id = %s")
            params.append(cluster_id)

        where_sql = " AND ".join(where)
        query = f"SELECT * FROM cluster_timeseries WHERE {where_sql} ORDER BY {sort_col} {sort_order}, cluster_id ASC"
        count_q = f"SELECT COUNT(*) AS total FROM cluster_timeseries WHERE {where_sql}"
        return self._paged(query, count_q, params, page, size)

    def latest_clusters(self, run_id: int) -> list[dict[str, Any]]:
        query = """
        WITH latest_t AS (
            SELECT MAX(sim_time_s) AS sim_time_s
            FROM cluster_timeseries
            WHERE run_id = %s
        )
        SELECT *
        FROM cluster_timeseries c
        WHERE c.run_id = %s
          AND c.sim_time_s = (SELECT sim_time_s FROM latest_t)
        ORDER BY c.cluster_id ASC
        """
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(query, (run_id, run_id))
                return [dict(r) for r in cur.fetchall()]

    def get_events(
        self,
        run_id: int,
        page: int,
        size: int,
        sort: str,
        order: str,
        event_type: Optional[str],
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> dict[str, Any]:
        sort_map = {
            "event_id": "event_id",
            "sim_time_s": "sim_time_s",
            "event_type": "event_type",
            "severity": "severity",
            "cluster_id": "cluster_id",
            "node_id": "node_id",
        }
        sort_col = sort_map.get(sort, "sim_time_s")
        sort_order = "DESC" if order.lower() == "desc" else "ASC"

        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if event_type:
            where.append("event_type ILIKE %s")
            params.append(f"%{event_type}%")
        if start_time is not None:
            where.append("sim_time_s >= %s")
            params.append(start_time)
        if end_time is not None:
            where.append("sim_time_s <= %s")
            params.append(end_time)

        where_sql = " AND ".join(where)
        query = f"SELECT * FROM events WHERE {where_sql} ORDER BY {sort_col} {sort_order}, event_id DESC"
        count_q = f"SELECT COUNT(*) AS total FROM events WHERE {where_sql}"
        return self._paged(query, count_q, params, page, size)

    def latest_events(self, run_id: int, limit: int) -> list[dict[str, Any]]:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    "SELECT * FROM events WHERE run_id = %s ORDER BY sim_time_s DESC, event_id DESC LIMIT %s",
                    (run_id, limit),
                )
                return [dict(r) for r in cur.fetchall()]

    def get_run_summary(self, run_id: int) -> Optional[dict[str, Any]]:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute("SELECT * FROM run_summary WHERE run_id = %s", (run_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def get_node_final_summary(
        self,
        run_id: int,
        page: int,
        size: int,
        sort: str,
        order: str,
        role: Optional[str],
        cluster_id: Optional[int],
    ) -> dict[str, Any]:
        sort_map = {
            "node_id": "node_id",
            "role": "role",
            "cluster_id": "cluster_id",
            "residual_j": "residual_j",
            "consumed_j": "consumed_j",
            "final_status": "final_status",
        }
        sort_col = sort_map.get(sort, "node_id")
        sort_order = "DESC" if order.lower() == "desc" else "ASC"

        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if role:
            where.append("role = %s")
            params.append(role)
        if cluster_id is not None:
            where.append("cluster_id = %s")
            params.append(cluster_id)

        where_sql = " AND ".join(where)
        query = f"SELECT * FROM node_final_summary WHERE {where_sql} ORDER BY {sort_col} {sort_order}"
        count_q = f"SELECT COUNT(*) AS total FROM node_final_summary WHERE {where_sql}"
        result = self._paged(query, count_q, params, page, size)

        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT node_id, role, cluster_id, residual_j, consumed_j, final_status
                    FROM node_final_summary
                    WHERE run_id = %s
                    ORDER BY residual_j ASC
                    LIMIT 10
                    """,
                    (run_id,),
                )
                result["top_lowest_residual"] = [dict(r) for r in cur.fetchall()]
        return result

    def get_raw_table(
        self,
        run_id: Optional[int],
        table_name: str,
        page: int,
        size: int,
        sort: str,
        order: str,
    ) -> dict[str, Any]:
        if table_name not in self.allowed_tables:
            raise ValueError("unsupported table")

        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table_name,),
                )
                cols = [r["column_name"] for r in cur.fetchall()]

        if not cols:
            raise ValueError("table has no readable columns")

        safe_sort = sort if sort in cols else self.allowed_tables[table_name]["default_sort"]
        safe_order = "DESC" if order.lower() == "desc" else "ASC"

        where = []
        params: list[Any] = []
        if run_id is not None and "run_id" in cols:
            where.append("run_id = %s")
            params.append(run_id)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        query = f"SELECT * FROM {table_name} {where_sql} ORDER BY {safe_sort} {safe_order}"
        count_q = f"SELECT COUNT(*) AS total FROM {table_name} {where_sql}"
        result = self._paged(query, count_q, params, page, size)
        result["table"] = table_name
        result["columns"] = cols
        return result

    @staticmethod
    def _event_category_case_sql() -> str:
        return """
            CASE
                WHEN LOWER(COALESCE(event_type, '') || ' ' || COALESCE(message, '')) LIKE '%%fail%%' THEN 'failure'
                WHEN LOWER(COALESCE(event_type, '') || ' ' || COALESCE(message, '')) LIKE '%%recov%%' THEN 'recovery'
                WHEN LOWER(COALESCE(event_type, '') || ' ' || COALESCE(message, '')) LIKE '%%agg%%' THEN 'aggregate'
                WHEN LOWER(COALESCE(event_type, '') || ' ' || COALESCE(message, '')) LIKE '%%relay%%' THEN 'relay'
                WHEN LOWER(COALESCE(event_type, '') || ' ' || COALESCE(message, '')) LIKE '%%traffic%%' THEN 'traffic'
                WHEN LOWER(COALESCE(event_type, '') || ' ' || COALESCE(message, '')) LIKE '%%milestone%%' THEN 'milestone'
                ELSE 'other'
            END
        """

    def get_cluster_final_summary(self, run_id: int) -> list[dict[str, Any]]:
        query = """
        WITH ranked AS (
            SELECT
                c.*,
                ROW_NUMBER() OVER (PARTITION BY c.cluster_id ORDER BY c.sim_time_s DESC) AS rn
            FROM cluster_timeseries c
            WHERE c.run_id = %s
        )
        SELECT
            cluster_id,
            status,
            original_ch_id,
            current_ch_id,
            mode,
            next_hop,
            members_count,
            raw_rx_cum,
            pending_raw,
            agg_tx_cum,
            relay_fwd_cum,
            ch_res_j,
            avg_mem_res_j,
            cluster_consumed_j,
            CASE WHEN current_ch_id IS DISTINCT FROM original_ch_id THEN TRUE ELSE FALSE END AS ch_changed,
            CASE
                WHEN LOWER(status) LIKE '%%recover%%' OR LOWER(mode) LIKE '%%recover%%' THEN TRUE
                WHEN current_ch_id IS DISTINCT FROM original_ch_id THEN TRUE
                ELSE FALSE
            END AS recovery_applied
        FROM ranked
        WHERE rn = 1
        ORDER BY cluster_id ASC
        """
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(query, (run_id,))
                return [dict(r) for r in cur.fetchall()]

    def get_run_overview_v2(self, run_id: int) -> dict[str, Any]:
        base = self.get_overview(run_id)
        metadata = base.get("metadata", {})
        summary = base.get("run_summary", {})

        raw_tx = float(summary.get("raw_tx_cum") or 0)
        raw_rx = float(summary.get("raw_rx_cum") or 0)
        agg_rx = float(summary.get("agg_rx_cum") or 0)

        result_summary = {
            "raw_tx_total": summary.get("raw_tx_cum", 0),
            "raw_rx_total": summary.get("raw_rx_cum", 0),
            "raw_delivery_pct": round((raw_rx / raw_tx * 100.0), 3) if raw_tx > 0 else 0.0,
            "agg_tx_total": summary.get("agg_tx_cum", 0),
            "agg_rx_total": summary.get("agg_rx_cum", 0),
            "agg_per_raw_rx": round((agg_rx / raw_rx), 6) if raw_rx > 0 else 0.0,
            "direct_agg_rx_total": summary.get("direct_agg_rx_cum", 0),
            "relayed_agg_rx_total": summary.get("relayed_agg_rx_cum", 0),
            "relay_forward_total": summary.get("relay_fwd_cum", 0),
            "failed_chs": summary.get("failed_chs", 0),
            "recovered_clusters": summary.get("recovered_clusters", 0),
            "pending_raw_total": summary.get("pending_raw_total", 0),
            "avg_residual_j": summary.get("avg_res_j", 0),
            "min_residual_j": summary.get("min_res_j", 0),
            "total_consumed_j": summary.get("consumed_j", 0),
        }

        return {
            "run_id": run_id,
            "run_identity": {
                "run_id": metadata.get("run_id"),
                "experiment_version": metadata.get("experiment_version"),
                "schema_version": metadata.get("schema_version"),
                "scenario_name": metadata.get("scenario_name"),
                "scenario_type": metadata.get("scenario_type"),
                "started_at": metadata.get("started_at"),
            },
            "configuration_summary": {
                "sim_time_s": metadata.get("sim_time_s"),
                "node_count": metadata.get("node_count"),
                "cluster_count": metadata.get("cluster_count"),
                "traffic_interval_s": metadata.get("traffic_interval_s"),
                "aggregation_interval_s": metadata.get("aggregation_interval_s"),
                "failure_time_s": metadata.get("failure_time_s"),
                "recovery_delay_s": metadata.get("recovery_delay_s"),
                "recovery_enabled": metadata.get("recovery_enabled"),
            },
            "result_summary": result_summary,
            "cluster_summary": self.get_cluster_final_summary(run_id),
            "counts": base.get("counts", {}),
            "event_stats": base.get("event_stats", {}),
            "integrity": base.get("integrity", {}),
            "raw": base,
        }

    def get_global_timeseries_inspection(
        self,
        run_id: int,
        from_time: Optional[float],
        to_time: Optional[float],
    ) -> list[dict[str, Any]]:
        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if from_time is not None:
            where.append("sim_time_s >= %s")
            params.append(from_time)
        if to_time is not None:
            where.append("sim_time_s <= %s")
            params.append(to_time)
        where_sql = " AND ".join(where)
        query = f"SELECT * FROM global_timeseries WHERE {where_sql} ORDER BY sim_time_s ASC"
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]

    def get_cluster_timeseries_inspection(
        self,
        run_id: int,
        cluster_id: Optional[int],
        from_time: Optional[float],
        to_time: Optional[float],
    ) -> list[dict[str, Any]]:
        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if cluster_id is not None:
            where.append("cluster_id = %s")
            params.append(cluster_id)
        if from_time is not None:
            where.append("sim_time_s >= %s")
            params.append(from_time)
        if to_time is not None:
            where.append("sim_time_s <= %s")
            params.append(to_time)

        where_sql = " AND ".join(where)
        query = f"SELECT * FROM cluster_timeseries WHERE {where_sql} ORDER BY sim_time_s ASC, cluster_id ASC"
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]

    def get_events_inspection(
        self,
        run_id: int,
        search: Optional[str],
        category: Optional[str],
        from_time: Optional[float],
        to_time: Optional[float],
        page: int,
        size: int,
        sort: str,
        order: str,
    ) -> dict[str, Any]:
        sort_map = {
            "event_id": "event_id",
            "sim_time_s": "sim_time_s",
            "event_type": "event_type",
            "severity": "severity",
            "category": "category",
        }
        sort_col = sort_map.get(sort, "sim_time_s")
        sort_order = "DESC" if order.lower() == "desc" else "ASC"

        cat_sql = self._event_category_case_sql()
        where = ["run_id = %s"]
        params: list[Any] = [run_id]
        if search:
            where.append("(message ILIKE %s OR event_type ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        if category:
            where.append(f"({cat_sql}) = %s")
            params.append(category.lower())
        if from_time is not None:
            where.append("sim_time_s >= %s")
            params.append(from_time)
        if to_time is not None:
            where.append("sim_time_s <= %s")
            params.append(to_time)

        where_sql = " AND ".join(where)
        query = f"""
        SELECT
            event_id,
            run_id,
            sim_time_s,
            event_type,
            severity,
            cluster_id,
            node_id,
            message,
            details,
            {cat_sql} AS category
        FROM events
        WHERE {where_sql}
        ORDER BY {sort_col} {sort_order}, event_id DESC
        """
        count_q = f"SELECT COUNT(*) AS total FROM events WHERE {where_sql}"
        return self._paged(query, count_q, params, page, size)

    def get_node_final_summary_inspection(
        self,
        run_id: int,
        cluster_id: Optional[int],
        role: Optional[str],
        sort: str,
        order: str,
        page: int,
        size: int,
    ) -> dict[str, Any]:
        data = self.get_node_final_summary(run_id, page, size, sort, order, role, cluster_id)
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT node_id, role, cluster_id, residual_j, consumed_j, final_status
                    FROM node_final_summary
                    WHERE run_id = %s
                    ORDER BY consumed_j DESC
                    LIMIT 10
                    """,
                    (run_id,),
                )
                data["top_highest_consumed"] = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    """
                    SELECT
                        role,
                        COUNT(*) AS nodes,
                        AVG(residual_j) AS avg_residual_j,
                        AVG(consumed_j) AS avg_consumed_j,
                        MIN(residual_j) AS min_residual_j,
                        MAX(consumed_j) AS max_consumed_j
                    FROM node_final_summary
                    WHERE run_id = %s
                    GROUP BY role
                    ORDER BY role
                    """,
                    (run_id,),
                )
                data["role_summary"] = [dict(r) for r in cur.fetchall()]
        return data

    def get_replay_snapshot(self, run_id: int, sim_time: float, window: float = 1.0) -> dict[str, Any]:
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM global_timeseries
                    WHERE run_id = %s
                    ORDER BY ABS(sim_time_s - %s), sim_time_s ASC
                    LIMIT 1
                    """,
                    (run_id, sim_time),
                )
                global_row = dict(cur.fetchone() or {})
                selected_time = global_row.get("sim_time_s")

                if selected_time is None:
                    cur.execute(
                        """
                        SELECT sim_time_s
                        FROM cluster_timeseries
                        WHERE run_id = %s
                        ORDER BY ABS(sim_time_s - %s), sim_time_s ASC
                        LIMIT 1
                        """,
                        (run_id, sim_time),
                    )
                    trow = cur.fetchone()
                    selected_time = trow["sim_time_s"] if trow else sim_time

                cur.execute(
                    """
                    SELECT *
                    FROM cluster_timeseries
                    WHERE run_id = %s AND sim_time_s = (
                        SELECT sim_time_s
                        FROM cluster_timeseries
                        WHERE run_id = %s
                        ORDER BY ABS(sim_time_s - %s), sim_time_s ASC
                        LIMIT 1
                    )
                    ORDER BY cluster_id ASC
                    """,
                    (run_id, run_id, selected_time),
                )
                cluster_rows = [dict(r) for r in cur.fetchall()]

                cat_sql = self._event_category_case_sql()
                cur.execute(
                    f"""
                    SELECT
                        event_id,
                        run_id,
                        sim_time_s,
                        event_type,
                        severity,
                        cluster_id,
                        node_id,
                        message,
                        details,
                        {cat_sql} AS category
                    FROM events
                    WHERE run_id = %s
                      AND sim_time_s >= %s
                      AND sim_time_s <= %s
                    ORDER BY sim_time_s ASC, event_id ASC
                    """,
                    (run_id, float(selected_time) - window, float(selected_time) + window),
                )
                event_rows = [dict(r) for r in cur.fetchall()]

                return {
                    "run_id": run_id,
                    "requested_time": sim_time,
                    "requested_time_s": sim_time,
                    "selected_time": selected_time,
                    "selected_time_s": selected_time,
                    "window": window,
                    "global": global_row,
                    "clusters": cluster_rows,
                    "events": event_rows,
                }

    @staticmethod
    def _derive_run_tags(row: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        recovery_enabled = bool(row.get("recovery_enabled"))
        tags.append("recovery_on" if recovery_enabled else "recovery_off")

        failure_time = row.get("failure_time_s")
        if failure_time is not None:
            try:
                f = float(failure_time)
                tags.append(f"failure_t{int(f) if float(int(f)) == f else f}")
            except Exception:
                pass

        delay = row.get("recovery_delay_s")
        if delay is not None:
            try:
                d = float(delay)
                tags.append(f"delay_{int(d) if float(int(d)) == d else d}s")
            except Exception:
                pass

        failed = int(row.get("failed_chs") or 0)
        recovered = int(row.get("recovered_clusters") or 0)
        if not recovery_enabled:
            tags.append("baseline")
        if recovered > 0:
            tags.append("recovered")
        if failed > 0 and recovered == 0:
            tags.append("failed_only")
        return tags

    @staticmethod
    def _run_base_select_sql() -> str:
        return """
            SELECT
                r.run_id,
                r.experiment_version,
                r.started_at,
                r.scenario_name,
                r.recovery_enabled,
                r.failure_time_s,
                r.recovery_delay_s,
                r.sim_time_s,
                r.node_count,
                r.cluster_count,
                rs.raw_tx_cum,
                rs.raw_rx_cum,
                rs.agg_rx_cum AS agg_rx_total,
                rs.consumed_j AS total_consumed_j,
                rs.min_res_j AS min_residual_j,
                rs.recovered_clusters,
                rs.failed_chs
            FROM runs r
            LEFT JOIN run_summary rs ON rs.run_id = r.run_id
        """

    def _analytics_where_sql(self, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        where: list[str] = []
        params: list[Any] = []

        exp_ver = filters.get("experiment_version")
        if exp_ver:
            where.append("r.experiment_version ILIKE %s")
            params.append(f"%{exp_ver}%")

        scenario_name = filters.get("scenario_name")
        if scenario_name:
            where.append("r.scenario_name ILIKE %s")
            params.append(f"%{scenario_name}%")

        recovery_enabled = filters.get("recovery_enabled")
        if recovery_enabled is not None:
            where.append("r.recovery_enabled = %s")
            params.append(bool(recovery_enabled))

        if filters.get("failure_time_s") is not None:
            where.append("r.failure_time_s = %s")
            params.append(filters["failure_time_s"])

        if filters.get("recovery_delay_s") is not None:
            where.append("r.recovery_delay_s = %s")
            params.append(filters["recovery_delay_s"])

        if filters.get("sim_time_s") is not None:
            where.append("r.sim_time_s = %s")
            params.append(filters["sim_time_s"])

        if filters.get("node_count") is not None:
            where.append("r.node_count = %s")
            params.append(filters["node_count"])

        if filters.get("cluster_count") is not None:
            where.append("r.cluster_count = %s")
            params.append(filters["cluster_count"])

        if filters.get("started_from") is not None:
            where.append("r.started_at >= %s")
            params.append(filters["started_from"])

        if filters.get("started_to") is not None:
            where.append("r.started_at <= %s")
            params.append(filters["started_to"])

        run_ids = filters.get("run_ids") or []
        if run_ids:
            placeholders = ",".join(["%s"] * len(run_ids))
            where.append(f"r.run_id IN ({placeholders})")
            params.extend(run_ids)

        where_sql = ""
        if where:
            where_sql = " WHERE " + " AND ".join(where)
        return where_sql, params

    @staticmethod
    def _with_derived_fields(row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        raw_tx = float(out.get("raw_tx_cum") or 0)
        raw_rx = float(out.get("raw_rx_cum") or 0)
        out["raw_delivery_pct"] = round((raw_rx / raw_tx) * 100.0, 3) if raw_tx > 0 else 0.0
        out["agg_rx_total"] = out.get("agg_rx_total") or 0
        out["total_consumed_j"] = out.get("total_consumed_j") or 0
        out["min_residual_j"] = out.get("min_residual_j") or 0
        out["recovered_clusters"] = out.get("recovered_clusters") or 0
        out["failed_chs"] = out.get("failed_chs") or 0
        out["tags"] = MonitorRepository._derive_run_tags(out)
        return out

    def get_analytics_runs(
        self,
        page: int,
        size: int,
        sort: str,
        order: str,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        sort_map = {
            "newest": "r.started_at DESC NULLS LAST, r.run_id DESC",
            "oldest": "r.started_at ASC NULLS LAST, r.run_id ASC",
            "started_at": "r.started_at",
            "run_id": "r.run_id",
            "raw_delivery_pct": "(CASE WHEN COALESCE(rs.raw_tx_cum, 0) > 0 THEN (COALESCE(rs.raw_rx_cum, 0)::float / rs.raw_tx_cum::float) * 100.0 ELSE 0 END)",
            "agg_rx_total": "COALESCE(rs.agg_rx_cum, 0)",
            "total_consumed_j": "COALESCE(rs.consumed_j, 0)",
            "min_residual_j": "COALESCE(rs.min_res_j, 0)",
            "recovered_clusters": "COALESCE(rs.recovered_clusters, 0)",
            "failed_chs": "COALESCE(rs.failed_chs, 0)",
        }

        where_sql, params = self._analytics_where_sql(filters)
        offset = (page - 1) * size
        base = self._run_base_select_sql()
        sort_key = sort_map.get(sort, "r.started_at")
        if sort in ("newest", "oldest"):
            order_sql = sort_key
        else:
            order_sql = f"{sort_key} {'DESC' if order.lower() == 'desc' else 'ASC'} NULLS LAST, r.run_id DESC"

        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM runs r LEFT JOIN run_summary rs ON rs.run_id = r.run_id {where_sql}", params)
                total = int(cur.fetchone()["total"])

                cur.execute(
                    f"{base} {where_sql} ORDER BY {order_sql} LIMIT %s OFFSET %s",
                    params + [size, offset],
                )
                rows = [self._with_derived_fields(dict(r)) for r in cur.fetchall()]

        return {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size if size > 0 else 0,
            "items": rows,
        }

    def _analytics_rows_all(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where_sql, params = self._analytics_where_sql(filters)
        base = self._run_base_select_sql()
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(f"{base} {where_sql} ORDER BY r.started_at DESC NULLS LAST, r.run_id DESC", params)
                return [self._with_derived_fields(dict(r)) for r in cur.fetchall()]

    def get_analytics_summary(self, filters: dict[str, Any]) -> dict[str, Any]:
        rows = self._analytics_rows_all(filters)
        n = len(rows)

        def avg(field: str) -> float:
            if n == 0:
                return 0.0
            return round(sum(float(r.get(field) or 0) for r in rows) / n, 6)

        recovery_runs = [r for r in rows if bool(r.get("recovery_enabled"))]
        recovery_den = len(recovery_runs)
        recovery_num = sum(1 for r in recovery_runs if int(r.get("recovered_clusters") or 0) > 0)
        recovery_success_rate = round((recovery_num / recovery_den) * 100.0, 3) if recovery_den > 0 else 0.0

        def pick(field: str, reverse: bool = True) -> Optional[dict[str, Any]]:
            if not rows:
                return None
            chosen = sorted(rows, key=lambda r: float(r.get(field) or 0), reverse=reverse)[0]
            return {
                "run_id": chosen.get("run_id"),
                "experiment_version": chosen.get("experiment_version"),
                "value": chosen.get(field),
            }

        energy_eff_best = None
        if rows:
            scored = sorted(
                rows,
                key=lambda r: (float(r.get("raw_delivery_pct") or 0) / max(float(r.get("total_consumed_j") or 0), 1e-9)),
                reverse=True,
            )
            winner = scored[0]
            energy_eff_best = {
                "run_id": winner.get("run_id"),
                "experiment_version": winner.get("experiment_version"),
                "delivery_per_j": round(float(winner.get("raw_delivery_pct") or 0) / max(float(winner.get("total_consumed_j") or 0), 1e-9), 6),
            }

        return {
            "filtered_runs": n,
            "averages": {
                "raw_delivery_pct": avg("raw_delivery_pct"),
                "agg_rx_total": avg("agg_rx_total"),
                "total_consumed_j": avg("total_consumed_j"),
                "min_residual_j": avg("min_residual_j"),
                "recovered_clusters": avg("recovered_clusters"),
                "failed_chs": avg("failed_chs"),
            },
            "recovery_success_rate_pct": recovery_success_rate,
            "highlights": {
                "best_delivery_run": pick("raw_delivery_pct", True),
                "best_energy_efficiency_run": energy_eff_best,
                "worst_min_residual_run": pick("min_residual_j", False),
                "most_recovered_clusters_run": pick("recovered_clusters", True),
                "highest_consumed_energy_run": pick("total_consumed_j", True),
            },
        }

    def get_analytics_charts(self, filters: dict[str, Any], group_by: Optional[str]) -> dict[str, Any]:
        rows = self._analytics_rows_all(filters)
        labels = [f"Run {r['run_id']}" for r in rows]
        by_run = {
            "labels": labels,
            "run_ids": [r.get("run_id") for r in rows],
            "raw_delivery_pct": [float(r.get("raw_delivery_pct") or 0) for r in rows],
            "agg_rx_total": [float(r.get("agg_rx_total") or 0) for r in rows],
            "total_consumed_j": [float(r.get("total_consumed_j") or 0) for r in rows],
            "min_residual_j": [float(r.get("min_residual_j") or 0) for r in rows],
            "recovered_clusters": [float(r.get("recovered_clusters") or 0) for r in rows],
        }

        grouped: list[dict[str, Any]] = []
        group_fields = {"recovery_enabled", "failure_time_s", "recovery_delay_s"}
        if group_by in group_fields:
            buckets: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                value = row.get(group_by)
                key = "null" if value is None else str(value)
                buckets.setdefault(key, []).append(row)
            for key, group_rows in sorted(buckets.items(), key=lambda kv: kv[0]):
                count = len(group_rows)
                grouped.append(
                    {
                        "group": key,
                        "count": count,
                        "avg_raw_delivery_pct": round(sum(float(r.get("raw_delivery_pct") or 0) for r in group_rows) / max(count, 1), 6),
                        "avg_agg_rx_total": round(sum(float(r.get("agg_rx_total") or 0) for r in group_rows) / max(count, 1), 6),
                        "avg_total_consumed_j": round(sum(float(r.get("total_consumed_j") or 0) for r in group_rows) / max(count, 1), 6),
                        "avg_min_residual_j": round(sum(float(r.get("min_residual_j") or 0) for r in group_rows) / max(count, 1), 6),
                        "avg_recovered_clusters": round(sum(float(r.get("recovered_clusters") or 0) for r in group_rows) / max(count, 1), 6),
                    }
                )

        return {
            "filtered_runs": len(rows),
            "by_run": by_run,
            "group_by": group_by,
            "grouped": grouped,
        }

    def get_analytics_cluster_final_for_runs(self, run_ids: list[int]) -> list[dict[str, Any]]:
        if not run_ids:
            return []
        placeholders = ",".join(["%s"] * len(run_ids))
        query = f"""
            WITH ranked AS (
                SELECT
                    c.*,
                    ROW_NUMBER() OVER (PARTITION BY c.run_id, c.cluster_id ORDER BY c.sim_time_s DESC) AS rn
                FROM cluster_timeseries c
                WHERE c.run_id IN ({placeholders})
            )
            SELECT
                run_id,
                cluster_id,
                sim_time_s,
                status,
                original_ch_id,
                current_ch_id,
                mode,
                next_hop,
                members_count,
                raw_rx_cum,
                pending_raw,
                agg_tx_cum,
                relay_fwd_cum,
                ch_res_j,
                avg_mem_res_j,
                cluster_consumed_j
            FROM ranked
            WHERE rn = 1
            ORDER BY run_id ASC, cluster_id ASC
        """
        with get_connection() as conn:
            with get_cursor(conn) as cur:
                cur.execute(query, run_ids)
                return [dict(r) for r in cur.fetchall()]
