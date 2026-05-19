from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple

import reflex as rx
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ...queries.metrics import timeseries
from ...queries.latest import latest_snapshot
from ...queries.features import features_5m
from ...queries.indicators import tech_indicators_1m, tech_indicators_adaptive
from ...queries.tags import tags_list
from ...queries.qc import qc_rules
from ...queries.realtime import get_sliding_window_data, realtime_data
# Alarm queries removed - not used in current implementation
# 캐시 시스템 제거됨 - 실시간 데이터가 더 중요


from .utils import (
    _to_float,
    _to_int,
    _fmt_s,
    _fmt_s_int,
    _to_str,
    _norm_window,
    _fmt_ts_local,
    _fmt_ts_short,
    _fmt_ts_time_only,
    _fmt_ts_short_chart,
    _mean_safe,
    _stdev_safe,
    _compute_indicators_fallback,
)


class DashboardState(rx.State):
    tag_name: Optional[str] = None
    window: str = "5 min"
    resolution: Optional[str] = None
    start_iso: Optional[str] = None  # kept for future use
    end_iso: Optional[str] = None
    range_mode: str = "relative"
    overlay_enabled: bool = False
    loading: bool = False
    series: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    latest: List[Dict[str, Any]] = []
    indicators: List[Dict[str, Any]] = []
    tags: List[str] = []
    qc: List[Dict[str, Any]] = []
    qc_min: Optional[float] = None
    qc_max: Optional[float] = None
    qc_min_s: str = ""
    qc_max_s: str = ""
    qc_label_s: str = "No QC"
    current_color: str = "#10b981"  # default green
    gauge_track_css: str = "conic-gradient(#e5e7eb 0 100%)"
    error: Optional[str] = None
    # KPI fields derived from `series`
    kpi_avg: Optional[float] = None
    kpi_count: int = 0  # number of buckets (rows) in current series
    kpi_min: Optional[float] = None
    kpi_max: Optional[float] = None
    # KPI formatted strings (0 포함하여 항상 표시)
    kpi_avg_s: str = "0.0"
    kpi_count_s: str = "0"
    kpi_min_s: str = "0.0"
    kpi_max_s: str = "0.0"
    # KPI rows for all tags (Dashboard)
    kpi_rows: List[Dict[str, Any]] = []
    # Mini chart data for each tag (recent 10-20 points)
    mini_chart_data: Dict[str, List[Dict[str, Any]]] = {}
    # Chart series visibility flags (기본: Average만 표시)
    show_avg: bool = True
    show_min: bool = True
    show_max: bool = True
    show_last: bool = True
    show_first: bool = True
    # Tech indicator visibility flags
    show_tech_avg: bool = True
    show_sma_10: bool = True
    show_sma_60: bool = True
    show_bb_upper: bool = True
    show_bb_lower: bool = True
    # Chart view mode toggle: True = Area mode (individual charts), False = Composed mode (single chart)
    chart_view_mode: bool = True  # True = Area, False = Composed
    
    # Area mode - individual chart selection (토글 버튼 그룹)
    trend_selected: str = "avg"  # avg, min, max, first, last
    tech_selected: str = "avg"   # avg, sma_10, sma_60, bb_upper, bb_lower
    
    # Composed mode - multiple selection (세그먼트 컨트롤 다중 선택)
    trend_composed_selected: list[str] = ["min", "max"]  # 기본값: min, max 선택  
    tech_composed_selected: list[str] = ["sma_10", "sma_60"]  # 기본값: SMA 10, 60 선택
    
    # Legacy toggles for composed mode (체크박스 방식)
    trend_chart_toggle: bool = True  # True = Area, False = Bar (legacy)
    tech_chart_toggle: bool = True   # True = Area, False = Line (legacy)
    # Current value for gauge
    current_value_s: str = "0.0"
    current_percent: int = 0
    # Auto refresh control
    auto_refresh: bool = False
    auto_interval_s: int = 15
    # Real-time data control (기본 활성화)
    realtime_mode: bool = True
    realtime_data: Dict[str, List[Dict[str, Any]]] = {}  # tag -> realtime data points
    realtime_interval_s: int = 10  # 10초 간격 (influx_hist 실제 데이터 간격에 맞춤)
    # Real-time loop control (중복 실행 방지)
    _realtime_loop_id: Optional[str] = None  # 현재 실행 중인 실시간 루프 ID
    _realtime_loop_running: bool = False     # 실시간 루프 실행 상태 플래그
    # Manual refresh token
    reload_token: int = 0
    
    # Checkbox toggle methods for composed mode
    def toggle_trend_composed_item(self, value: str, checked: bool):
        """Toggle individual trend item in composed mode"""
        if checked and value not in self.trend_composed_selected:
            self.trend_composed_selected.append(value)
        elif not checked and value in self.trend_composed_selected:
            self.trend_composed_selected.remove(value)
    
    def toggle_tech_composed_item(self, value: str, checked: bool):
        """Toggle individual tech indicator in composed mode"""
        if checked and value not in self.tech_composed_selected:
            self.tech_composed_selected.append(value)
        elif not checked and value in self.tech_composed_selected:
            self.tech_composed_selected.remove(value)
    
    # Alarm system state
    active_alarms: List[Dict[str, Any]] = []
    alarm_summary: Dict[str, Any] = {}
    recent_anomalies: List[Dict[str, Any]] = []
    alarm_refresh_token: int = 0
    
    # Modal state
    detail_modal_open: bool = False
    selected_sensor_data: Dict[str, Any] = {}
    
    # Sidebar state
    sidebar_collapsed: bool = False

    # 통신 장애 여부(파생): DSN 미설정/커넥션/타임아웃 계열 에러를 감지
    @rx.var
    def comms_down(self) -> bool:  # type: ignore[override]
        if not self.error:
            return False
        e = str(self.error).lower()
        return (
            ("ts_dsn" in e)
            or ("connect" in e)
            or ("timeout" in e)
        )

    @rx.var
    def alert_sensors(self) -> List[Dict[str, Any]]:  # type: ignore[override]
        """위험/경계 상태 센서 (status_level >= 1)"""
        alerts = []
        for row in (self.kpi_rows or []):
            status_level = row.get("status_level", 0)
            if status_level >= 1:  # 경계(1) 또는 위험(2)
                alerts.append(row)
        # 위험(2) 우선, 그 다음 경계(1) 순으로 정렬
        alerts.sort(key=lambda x: (x.get("status_level", 0), x.get("tag_name", "")), reverse=True)
        return alerts

    @rx.var  
    def normal_sensors(self) -> List[Dict[str, Any]]:  # type: ignore[override]
        """정상 상태 센서 (status_level == 0)"""
        normal = []
        for row in (self.kpi_rows or []):
            status_level = row.get("status_level", 0)
            if status_level == 0:  # 정상
                normal.append(row)
        # 태그명 순으로 정렬
        normal.sort(key=lambda x: x.get("tag_name", ""))
        return normal

    @rx.var
    def alert_count(self) -> int:  # type: ignore[override]
        """전체 알람 센서 개수"""
        return len(self.alert_sensors)

    def get_mini_chart_data(self, tag_name: str) -> List[Dict[str, Any]]:
        """특정 태그의 미니 차트 데이터 반환"""
        return self.mini_chart_data.get(tag_name, [])

    @rx.var
    def series_for_tag(self) -> List[Dict[str, Any]]:  # type: ignore[override]
        if self.tag_name:
            return [r for r in (self.series or []) if r.get("tag_name") == self.tag_name]
        return self.series or []

    @rx.var
    def indicators_for_tag(self) -> List[Dict[str, Any]]:  # type: ignore[override]
        if self.tag_name:
            return [r for r in (self.indicators or []) if r.get("tag_name") == self.tag_name]
        return self.indicators or []

    @rx.var
    def series_for_tag_desc_with_num(self) -> List[Dict[str, Any]]:  # type: ignore[override]
        rows = list(self.series_for_tag or [])
        rows.sort(key=lambda r: (r.get("bucket") or ""), reverse=True)
        numbered: List[Dict[str, Any]] = []
        for idx, r in enumerate(rows):
            row = dict(r)
            row["num"] = idx + 1  # NUM 오름차순 (1,2,3,...)
            numbered.append(row)
        return numbered

    @rx.var
    def indicators_for_tag_desc(self) -> List[Dict[str, Any]]:  # type: ignore[override]
        rows = list(self.indicators_for_tag or [])
        rows.sort(key=lambda r: (r.get("bucket") or ""), reverse=True)
        return rows

    @rx.var
    def indicators_for_tag_desc_with_num(self) -> List[Dict[str, Any]]:  # type: ignore[override]
        rows = list(self.indicators_for_tag_desc or [])
        numbered: List[Dict[str, Any]] = []
        for idx, r in enumerate(rows):
            row = dict(r)
            row["num"] = idx + 1  # NUM 오름차순
            numbered.append(row)
        return numbered

    @rx.event(background=True)
    async def load(self):
        # 트렌드 페이지 감지를 먼저 수행 (전체 함수에서 사용)
        is_trend_page = False
        try:
            current_path = self.router.url.path
            is_trend_page = (current_path == "/trend")
        except:
            pass
            
        async with self:
            self.loading = True
            self.error = None
            # 차트 원래 시리즈(Avg/Min/Max/Last/First) 기본 표시 강제
            self.show_avg = True
            self.show_min = True
            self.show_max = True
            self.show_last = True
            self.show_first = True
            # 트렌드 페이지 초기화는 데이터 로딩 완료 후로 지연 (깜빡임 방지)
                
        try:
            win = _norm_window(self.window)

            # Use user-provided absolute range only when provided
            start_iso = self.start_iso
            end_iso = self.end_iso
            
            # 캐시 시스템 제거 - 실시간 데이터 우선으로 직접 쿼리 실행
            if not is_trend_page:
                data_coro = timeseries(win, None, self.resolution, start_iso, end_iso)  # for Dashboard KPIs we need all tags
                feats_coro = features_5m(win, self.tag_name)
                last_coro = latest_snapshot(None)
                qc_coro = qc_rules(None)
            else:
                # 트렌드 페이지에서는 선택된 태그만 로딩
                data_coro = timeseries(win, self.tag_name, self.resolution, start_iso, end_iso)
                feats_coro = asyncio.create_task(asyncio.sleep(0, result=[]))
                last_coro = asyncio.create_task(asyncio.sleep(0, result=[]))
                qc_coro = asyncio.create_task(asyncio.sleep(0, result=[]))
            
            # 기술지표도 시간 범위에 따른 적응적 해상도 사용
            inds_coro = tech_indicators_adaptive(win, self.tag_name)
            tags_coro = tags_list()

            data_raw, feats, last, inds_raw, tags_rows, qc_rows = await asyncio.gather(
                data_coro, feats_coro, last_coro, inds_coro, tags_coro, qc_coro
            )
            
            # Alarm data (not implemented yet, set to empty)
            alarms_raw, alarm_summary_raw, recent_anomalies_raw = [], {}, []

            # Safe copies and normalization
            data: List[Dict[str, Any]] = []
            for r in data_raw or []:
                row = dict(r)
                row["avg"] = _to_float(row.get("avg"))
                row["min"] = _to_float(row.get("min"))
                row["max"] = _to_float(row.get("max"))
                row["last"] = _to_float(row.get("last"))
                row["first"] = _to_float(row.get("first"))
                row["n"] = _to_int(row.get("n"))
                if row.get("bucket") is not None:
                    row["bucket"] = _to_str(row["bucket"])
                    # X축용 포맷된 타임스탬프 (년-월-일 시:분)
                    row["bucket_formatted"] = _fmt_ts_short_chart(row.get("bucket"))
                # formatted strings for table rendering (avoid client JS expressions)
                row["avg_s"] = _fmt_s(row.get("avg"), 2)
                row["min_s"] = _fmt_s(row.get("min"), 2)
                row["max_s"] = _fmt_s(row.get("max"), 2)
                row["last_s"] = _fmt_s(row.get("last"), 2)
                row["first_s"] = _fmt_s(row.get("first"), 2)
                row["n_s"] = _fmt_s_int(row.get("n"))
                data.append(row)

            inds: List[Dict[str, Any]] = []
            for r in inds_raw or []:
                row = dict(r)
                for k in ("avg", "sma_10", "sma_60", "bb_top", "bb_bot", "slope_60"):
                    row[k] = _to_float(row.get(k))
                if row.get("bucket") is not None:
                    row["bucket"] = _to_str(row["bucket"])
                    # X축용 포맷된 타임스탬프 (년-월-일 시:분)
                    row["bucket_formatted"] = _fmt_ts_short_chart(row.get("bucket"))
                row["bucket_s"] = _fmt_ts_local(row.get("bucket"))
                # formatted strings for table rendering
                row["avg_s"] = _fmt_s(row.get("avg"), 2)
                row["sma_10_s"] = _fmt_s(row.get("sma_10"), 2)
                row["sma_60_s"] = _fmt_s(row.get("sma_60"), 2)
                row["bb_top_s"] = _fmt_s(row.get("bb_top"), 2)
                row["bb_bot_s"] = _fmt_s(row.get("bb_bot"), 2)
                row["slope_60_s"] = _fmt_s(row.get("slope_60"), 2)
                inds.append(row)

            # If no indicator rows for the selected tag, compute a safe fallback from series
            sel_tag = self.tag_name
            has_for_sel = any((r.get("tag_name") == sel_tag) for r in inds) if sel_tag else bool(inds)
            if not has_for_sel:
                # Use series rows for the selected tag to derive indicators
                base_rows = [
                    {"bucket": _to_str(r.get("bucket")), "tag_name": r.get("tag_name"), "avg": _to_float(r.get("avg"))}
                    for r in data if (sel_tag is None or r.get("tag_name") == sel_tag)
                ]
                base_rows.sort(key=lambda r: (r.get("bucket") or ""))  # ASC
                fb = _compute_indicators_fallback(base_rows)
                inds = []
                for r in fb:
                    row = dict(r)
                    if row.get("bucket") is not None:
                        row["bucket"] = _to_str(row["bucket"])
                        # X축용 포맷된 타임스탬프 (년-월-일 시:분)
                        row["bucket_formatted"] = _fmt_ts_short_chart(row.get("bucket"))
                    row["bucket_s"] = _fmt_ts_local(row.get("bucket"))
                    row["avg_s"] = _fmt_s(row.get("avg"), 2)
                    row["sma_10_s"] = _fmt_s(row.get("sma_10"), 2)
                    row["sma_60_s"] = _fmt_s(row.get("sma_60"), 2)
                    row["bb_top_s"] = _fmt_s(row.get("bb_top"), 2)
                    row["bb_bot_s"] = _fmt_s(row.get("bb_bot"), 2)
                    row["slope_60_s"] = _fmt_s(row.get("slope_60"), 2)
                    inds.append(row)

            ind_index: Dict[Tuple[Optional[str], Optional[str]], Dict[str, Any]] = {
                (row.get("bucket"), row.get("tag_name")): row for row in inds
            }

            merged: List[Dict[str, Any]] = []
            for r in data:
                key = (r.get("bucket"), r.get("tag_name"))
                ind = ind_index.get(key)
                row = dict(r)
                if ind:
                    row.update({
                        "sma_10": ind.get("sma_10"),
                        "sma_60": ind.get("sma_60"),
                        "bb_top": ind.get("bb_top"),
                        "bb_bot": ind.get("bb_bot"),
                        "slope_60": ind.get("slope_60"),
                    })
                    bt, bb = row.get("bb_top"), row.get("bb_bot")
                    row["bb_range"] = (bt - bb) if (bt is not None and bb is not None) else None
                # ensure formatted strings exist after merge as well (for table use)
                row["avg_s"] = _fmt_s(row.get("avg"), 2)
                row["min_s"] = _fmt_s(row.get("min"), 2)
                row["max_s"] = _fmt_s(row.get("max"), 2)
                row["last_s"] = _fmt_s(row.get("last"), 2)
                row["first_s"] = _fmt_s(row.get("first"), 2)
                row["n_s"] = _fmt_s_int(row.get("n"))
                if ind:
                    row["sma_10_s"] = _fmt_s(row.get("sma_10"), 2)
                    row["sma_60_s"] = _fmt_s(row.get("sma_60"), 2)
                    row["bb_top_s"] = _fmt_s(row.get("bb_top"), 2)
                    row["bb_bot_s"] = _fmt_s(row.get("bb_bot"), 2)
                    row["slope_60_s"] = _fmt_s(row.get("slope_60"), 2)
                merged.append(row)

            merged.sort(key=lambda r: ((r.get("tag_name") or ""), (r.get("bucket") or "")))
            inds.sort(key=lambda r: ((r.get("tag_name") or ""), (r.get("bucket") or "")))

            tag_values: List[str] = []
            for t in tags_rows or []:
                if isinstance(t, dict) and "tag_name" in t:
                    tag_values.append(str(t["tag_name"]))
                else:
                    tag_values.append(str(t))

            # Build percentile map for alarm evaluation (latest features per tag)
            perc_map: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
            for f in (feats or []):
                t = f.get("tag_name")
                b = _to_str(f.get("bucket")) or ""
                key = (t, b)
                if t is None:
                    continue
                # keep highest bucket per tag
                if t not in perc_map or b > (perc_map[t][2] if len(perc_map[t]) > 2 else ""):
                    p10 = _to_float(f.get("p10_5m"))
                    p90 = _to_float(f.get("p90_5m"))
                    perc_map[t] = (p10, p90, b)  # store bucket for comparison
            # Process latest rows with Comm/Alarm
            processed_latest: List[Dict[str, Any]] = []
            # infer bucket seconds from resolution/window
            res = self.resolution or ("1m" if win in {"1 hour", "4 hours", "24 hours"} else "1h")
            bucket_seconds = 60 if res == "1m" else (600 if res == "10m" else 3600)
            # Ensure timezone-aware subtraction
            now_ts = datetime.now(ts_dt.tzinfo) if ("ts_dt" in locals() and ts_dt.tzinfo) else datetime.now()
            for r in (last or []):
                row = dict(r)
                ts_raw = r.get("ts")
                try:
                    ts_dt = datetime.fromisoformat(str(ts_raw))
                except Exception:  # noqa: BLE001
                    ts_dt = now_ts - timedelta(days=365)
                # Recompute now_ts with tz of ts_dt to avoid naive/aware mismatch
                now_local = datetime.now(ts_dt.tzinfo) if ts_dt.tzinfo else datetime.now()
                age = (now_local - ts_dt).total_seconds()
                comm_ok = age <= bucket_seconds * 2
                comm_label = "OK" if comm_ok else "STALE"
                p = perc_map.get(r.get("tag_name", ""), (None, None, ""))
                p10 = p[0]
                p90 = p[1]
                val = _to_float(r.get("value"))
                alarm = False
                if val is None or not comm_ok:
                    alarm = True
                elif p10 is not None and p90 is not None and (val < p10 or val > p90):
                    alarm = True
                row["comm_label"] = comm_label
                row["alarm_label"] = "Alarm" if alarm else "-"
                processed_latest.append(row)

            # 최신 스냅샷도 시간 내림차순 정렬
            try:
                processed_latest.sort(key=lambda r: str(r.get("ts") or ""), reverse=True)
            except Exception:  # noqa: BLE001
                pass

            async with self:
                # 최초 기동 시: 선택 태그가 없으면 목록의 첫 번째 태그로 자동 설정
                if not self.tag_name:
                    for tv in tag_values:
                        if tv:
                            self.tag_name = tv
                            break
                # 트렌드 페이지에서는 실시간 추가된 데이터 포인트 제거 (깜빡임 없이)
                if is_trend_page:
                    # 기존 시리즈 데이터가 있으면 보존하면서 필터링, 없으면 새 데이터 사용
                    if merged:
                        # 이력 데이터인지 판단: bucket 형식이나 n 값으로 구분
                        filtered_series = []
                        for item in merged:
                            bucket = item.get("bucket", "")
                            # ISO 형식의 긴 타임스탬프면 실시간 데이터일 가능성 높음
                            if isinstance(bucket, str) and ("T" in bucket and len(bucket) > 20):
                                continue  # 실시간 데이터 스킵
                            filtered_series.append(item)
                        
                        if len(filtered_series) > 0:
                            self.series = filtered_series
                            print(f"📊 트렌드 페이지: 이력 데이터 {len(filtered_series)}개 로딩 완료")
                        else:
                            # 필터링 후 데이터가 없으면 원본 사용 (빈 상태 방지)
                            self.series = merged
                            print(f"📊 트렌드 페이지: 전체 데이터 {len(merged)}개 로딩 (필터링 없음)")
                    else:
                        # 기존 시리즈 데이터 유지 (빈 상태 방지)
                        if not self.series:
                            self.series = []
                        print(f"📊 트렌드 페이지: 기존 데이터 유지")
                else:
                    self.series = merged
                self.features = list(feats or [])
                self.latest = processed_latest
                self.indicators = inds
                print(f"🔍 DEBUG: Loaded {len(inds)} indicator records for window '{win}', tag: '{self.tag_name}'")
                self.tags = sorted({tv for tv in tag_values if tv})
                self.qc = list(qc_rows or [])
                # Assign alarm data
                self.active_alarms = list(alarms_raw or [])
                self.alarm_summary = alarm_summary_raw or {}
                self.recent_anomalies = list(recent_anomalies_raw or [])
                # Build KPI rows for all tags
                rows_by_tag: Dict[str, List[Dict[str, Any]]] = {}
                for r in merged:
                    t = str(r.get("tag_name") or "")
                    if not t:
                        continue
                    rows_by_tag.setdefault(t, []).append(r)
                latest_by_tag: Dict[str, Any] = {}
                for r in processed_latest:
                    latest_by_tag[str(r.get("tag_name"))] = r
                # QC map
                qc_by_tag: Dict[str, Dict[str, Any]] = {}
                for r in qc_rows or []:
                    try:
                        qc_by_tag[str(r.get("tag_name"))] = dict(r)
                    except Exception:  # noqa: BLE001
                        continue
                krows: List[Dict[str, Any]] = []
                
                # 미니 차트 데이터 준비 (윈도우에 따른 적절한 개수)
                mini_data: Dict[str, List[Dict[str, Any]]] = {}
                for tag in rows_by_tag.keys():
                    tag_rows = rows_by_tag[tag]
                    # 시간 순서로 정렬 (모든 데이터 사용)
                    sorted_rows = sorted(tag_rows, key=lambda x: str(x.get("bucket") or ""))
                    
                    # 미니 차트용 데이터 형식으로 변환 (avg 필드 사용)
                    chart_data = []
                    for row in sorted_rows:
                        avg_val = row.get("avg")
                        if avg_val is not None:
                            chart_data.append({
                                "bucket": _fmt_ts_short(row.get("bucket")),
                                "avg": float(avg_val),
                                "bucket_full": row.get("bucket")  # 디버깅용 전체 타임스탬프
                            })
                    mini_data[tag] = chart_data
                
                for t in sorted(rows_by_tag.keys()):
                    try:
                        arr = rows_by_tag[t]
                        arr_sorted = sorted(arr, key=lambda x: str(x.get("bucket") or ""))
                        avgs = [v.get("avg") for v in arr if isinstance(v.get("avg"), (int, float))]
                        mins = [v.get("min") for v in arr if isinstance(v.get("min"), (int, float))]
                        maxs = [v.get("max") for v in arr if isinstance(v.get("max"), (int, float))]
                        cnt = len(arr)
                        latest_ts = latest_by_tag.get(t, {}).get("ts")
                        # window first/last (시계열 내 첫/마지막 버킷의 first/last 컬럼)
                        first_in_win = _to_float(arr_sorted[0].get("first")) if arr_sorted else None
                        last_in_win = _to_float(arr_sorted[-1].get("last")) if arr_sorted else None
                        prev_last_in_win = _to_float(arr_sorted[-2].get("last")) if len(arr_sorted) >= 2 else None
                        # delta: 최근 두 버킷의 last 변화율(%) - 실제 계산
                        delta_pct: float = 0.0
                        try:
                            if last_in_win is not None and prev_last_in_win not in (None, 0):
                                delta_pct = (float(last_in_win - prev_last_in_win) / abs(float(prev_last_in_win))) * 100.0
                        except Exception:
                            delta_pct = 0.0
                        # gauge percent: 값에 기반한 간단한 계산 (100을 기준으로 정규화)
                        gauge_pct: float = 0.0
                        qc = qc_by_tag.get(t, {})
                        def _fv(x):
                            try:
                                return float(x) if x is not None else None
                            except Exception:
                                return None
                        warn_min = _fv(qc.get("warn_min"))
                        warn_max = _fv(qc.get("warn_max"))
                        crit_min = _fv(qc.get("crit_min"))
                        crit_max = _fv(qc.get("crit_max"))
                        hard_min = _fv(qc.get("min_val"))
                        hard_max = _fv(qc.get("max_val"))
                        
                        # 게이지 퍼센트: 실제 데이터 기반 동적 계산
                        gauge_pct: float = 0.0
                        try:
                            # QC 범위가 있으면 QC 기준으로 계산
                            if (
                                last_in_win is not None and
                                hard_min is not None and
                                hard_max is not None and
                                hard_max > hard_min
                            ):
                                pos = (float(last_in_win) - hard_min) / (hard_max - hard_min)
                                gauge_pct = max(0.0, min(100.0, pos * 100.0))
                            # QC 범위가 없으면 윈도우 범위 기준으로 계산
                            elif last_in_win is not None:
                                win_min = float(min(mins)) if mins else None
                                win_max = float(max(maxs)) if maxs else None
                                if (
                                    win_min is not None and
                                    win_max is not None and
                                    win_max > win_min
                                ):
                                    pos = (float(last_in_win) - win_min) / (win_max - win_min)
                                    gauge_pct = max(0.0, min(100.0, pos * 100.0))
                                else:
                                    # 범위를 구할 수 없으면 절대값 기준으로 계산
                                    if float(last_in_win) >= 0:
                                        gauge_pct = min(100.0, abs(float(last_in_win)) / 200.0 * 100.0)
                                    else:
                                        gauge_pct = max(0.0, 100.0 - abs(float(last_in_win)) / 50.0 * 100.0)
                        except Exception:
                            gauge_pct = 50.0  # 기본값
                        
                        # severity by qc ranges
                        severity = 0
                        if last_in_win is not None:
                            if (hard_min is not None and last_in_win < hard_min) or (hard_max is not None and last_in_win > hard_max):
                                severity = 2
                            elif (crit_min is not None and last_in_win < crit_min) or (crit_max is not None and last_in_win > crit_max):
                                severity = 2
                            elif (warn_min is not None and last_in_win < warn_min) or (warn_max is not None and last_in_win > warn_max):
                                severity = 1

                        status_level = 0 if severity == 0 else (1 if severity == 1 else 2)
                        
                        # 테스트용 임시 알람 상태 (gauge_pct 기준)
                        if severity == 0:
                            # 특별 케이스: 음수값은 항상 위험 (최우선)
                            if last_in_win is not None and last_in_win < 0:
                                status_level = 2
                            elif gauge_pct >= 90:  # 90% 이상 → 위험 (빨강)
                                status_level = 2
                            elif gauge_pct >= 70:  # 70% 이상 → 경고 (노랑)
                                status_level = 1
                        qc_label_s = (
                            (f"{hard_min:.2f} ~ {hard_max:.2f}" if (hard_min is not None and hard_max is not None) else (f"{win_min:.2f} ~ {win_max:.2f}" if (win_min is not None and win_max is not None) else ""))
                        )
                        # 통신 상태 가져오기
                        latest_tag_data = latest_by_tag.get(t, {})
                        comm_status = latest_tag_data.get("is_comm_ok", True)
                        comm_text = "OK" if comm_status else "ERR"
                        
                        krows.append({
                            "tag_name": t,
                            # 메인 표시는 마지막 값
                            "value_s": _fmt_s(last_in_win if last_in_win is not None else _to_float(latest_by_tag.get(t, {}).get("value")), 1),
                            "ts_s": _fmt_ts_short(str(latest_ts) if latest_ts is not None else None),
                            "avg_s": _fmt_s((sum(avgs) / len(avgs)) if avgs else 0.0, 1),
                            "count_s": _fmt_s_int(cnt),
                            "min_s": _fmt_s(min(mins) if mins else 0.0, 1),
                            "max_s": _fmt_s(max(maxs) if maxs else 0.0, 1),
                            "first_s": _fmt_s(first_in_win, 1) if first_in_win is not None else "0.0",
                            "last_s": _fmt_s(last_in_win, 1) if last_in_win is not None else "0.0",
                            "delta_pct": round(delta_pct, 2),
                            "delta_s": f"{delta_pct:+.2f}%",
                            "gauge_pct": round(gauge_pct, 1),
                            "status_level": status_level,
                            "range_label": qc_label_s,
                            "mini_chart_data": mini_data.get(t, []),
                            "comm_status": comm_status,
                            "comm_text": comm_text,
                            "qc_min": hard_min,
                            "qc_max": hard_max,
                            "unit": "",  # 나중에 테이블에서 가져올 예정
                        })
                    except Exception:
                        krows.append({
                            "tag_name": t,
                            "value_s": "Error",
                            "ts_s": "",
                            "avg_s": "0.0",
                            "count_s": "0",
                            "min_s": "0.0",
                            "max_s": "0.0",
                            "first_s": "0.0",
                            "last_s": "0.0",
                            "delta_pct": 0.0,
                            "delta_s": "±0.0%",
                            "gauge_pct": 0.0,
                            "status_level": 2,  # Indicate error status
                            "range_label": "Error",
                            "mini_chart_data": [],
                            "unit": "",
                        })
                # 실시간 모드일 경우 각 행에 5초 간격 실시간 차트 데이터 추가
                if self.realtime_mode:
                    # 모든 태그에 대해 5초 간격 실시간 데이터 가져오기
                    realtime_tasks = []
                    for tag in rows_by_tag.keys():
                        realtime_tasks.append(realtime_data(tag, window_seconds=300, interval_seconds=5))   # 5분 범위, 5초 간격
                    
                    try:
                        realtime_results = await asyncio.gather(*realtime_tasks, return_exceptions=True)
                        
                        for i, krow in enumerate(krows):
                            tag_name = krow.get("tag_name")
                            if tag_name:
                                # 해당 태그의 실시간 데이터 찾기
                                tag_idx = list(rows_by_tag.keys()).index(tag_name) if tag_name in rows_by_tag else -1
                                if 0 <= tag_idx < len(realtime_results):
                                    rt_raw = realtime_results[tag_idx]
                                    if not isinstance(rt_raw, Exception):
                                        # 5초 간격 데이터 형식으로 변환 (최근 1분)
                                        rt_data = []
                                        for point in rt_raw[-6:]:  # 최근 1분(6개 포인트)만 사용
                                            bucket_time = _fmt_ts_time_only(point.get("bucket"))
                                            # 타입 정규화: value를 float으로 강제 변환
                                            raw_value = point.get("value", 0)
                                            try:
                                                clean_value = float(raw_value) if raw_value is not None else 0.0
                                            except (ValueError, TypeError):
                                                clean_value = 0.0
                                            
                                            rt_data.append({
                                                "bucket": str(bucket_time),  # 문자열 보장
                                                "value": clean_value,        # float 보장
                                                "ts": point.get("timestamp", point.get("bucket"))
                                            })
                                        
                                        krows[i]["realtime_chart_data"] = rt_data
                                        # 실시간 데이터 저장
                                        self.realtime_data[tag_name] = rt_data
                                    else:
                                        # 에러 발생 시 기존 mini_data 사용
                                        chart_data = mini_data.get(tag_name, [])
                                        rt_data = []
                                        for point in chart_data[-6:]:
                                            bucket_time = _fmt_ts_time_only(point.get("bucket_full", point.get("bucket")))
                                            # 타입 정규화: avg를 float으로 강제 변환
                                            raw_value = point.get("avg", 0)
                                            try:
                                                clean_value = float(raw_value) if raw_value is not None else 0.0
                                            except (ValueError, TypeError):
                                                clean_value = 0.0
                                            
                                            rt_data.append({
                                                "bucket": str(bucket_time),
                                                "value": clean_value,
                                                "ts": point.get("bucket_full", point.get("bucket"))
                                            })
                                        krows[i]["realtime_chart_data"] = rt_data
                                        self.realtime_data[tag_name] = rt_data
                    except Exception as e:
                        # 🔧 오류 처리 개선: 적절한 로깅으로 교체
                        import logging
                        logging.error(f"실시간 데이터 로딩 실패: {e}", exc_info=True)
                        # 에러 발생 시 기존 로직 사용
                        for i, krow in enumerate(krows):
                            tag_name = krow.get("tag_name")
                            if tag_name:
                                chart_data = mini_data.get(tag_name, [])
                                rt_data = []
                                for point in chart_data[-6:]:
                                    bucket_time = _fmt_ts_time_only(point.get("bucket_full", point.get("bucket")))
                                    rt_data.append({
                                        "bucket": bucket_time,
                                        "value": point.get("avg", 0),
                                        "ts": point.get("bucket_full", point.get("bucket"))
                                    })
                                krows[i]["realtime_chart_data"] = rt_data
                                self.realtime_data[tag_name] = rt_data
                
                if not is_trend_page:
                    self.kpi_rows = krows
                    print(f"🔍 KPI 행 생성 완료 - 총 {len(krows)}개 태그")
                else:
                    # 트렌드 페이지에서는 KPI 행 생성 스킵 (성능 최적화)
                    self.kpi_rows = []
                    print(f"⚡ 트렌드 페이지: KPI 행 생성 스킵 - 성능 최적화")
                
                # extract qc for selected tag
                sel_qc = None
                for r in self.qc:
                    if not self.tag_name or r.get("tag_name") == self.tag_name:
                        sel_qc = r
                        break
                def _pick(keys: list[str]) -> Optional[float]:
                    if not sel_qc:
                        return None
                    for k in keys:
                        if k in sel_qc and sel_qc[k] is not None:
                            try:
                                return float(sel_qc[k])
                            except Exception:
                                pass
                    return None
                self.qc_min = _pick(["min_val", "min", "min_allowed", "lower", "lower_bound"])  # type: ignore[list-item]
                self.qc_max = _pick(["max_val", "max", "max_allowed", "upper", "upper_bound"])  # type: ignore[list-item]
                self.qc_min_s = _fmt_s(self.qc_min, 1) if self.qc_min is not None else ""
                self.qc_max_s = _fmt_s(self.qc_max, 1) if self.qc_max is not None else ""
                if self.qc_min_s and self.qc_max_s:
                    self.qc_label_s = f"{self.qc_min_s} ~ {self.qc_max_s}"
                elif self.qc_min_s:
                    self.qc_label_s = self.qc_min_s
                elif self.qc_max_s:
                    self.qc_label_s = self.qc_max_s
                else:
                    self.qc_label_s = "No QC"
                # KPIs (현재 화면에 표시되는 범위 기준: 태그 필터 적용)
                effective = merged if not self.tag_name else [r for r in merged if r.get("tag_name") == self.tag_name]
                avgs = [r.get("avg") for r in effective if isinstance(r.get("avg"), (int, float))]
                mins = [r.get("min") for r in effective if isinstance(r.get("min"), (int, float))]
                maxs = [r.get("max") for r in effective if isinstance(r.get("max"), (int, float))]
                self.kpi_count = len(effective)
                self.kpi_avg = round((sum(avgs) / len(avgs)), 1) if avgs else 0.0
                self.kpi_min = round(min(mins), 1) if mins else 0.0
                self.kpi_max = round(max(maxs), 1) if maxs else 0.0
                # formatted strings for KPI
                self.kpi_count_s = _fmt_s_int(self.kpi_count)
                self.kpi_avg_s = _fmt_s(self.kpi_avg, 1)
                self.kpi_min_s = _fmt_s(self.kpi_min, 1)
                self.kpi_max_s = _fmt_s(self.kpi_max, 1)
                # consume reload token (캐시 제거로 항상 리셋)
                self.reload_token = 0
                # Current value (selected tag) for gauge
                cur: Optional[float] = None
                for r in (processed_latest or []):
                    if r.get("tag_name") == self.tag_name:
                        cur = _to_float(r.get("value"))
                        break
                cur = cur if cur is not None else 0.0
                self.current_value_s = _fmt_s(cur, 1)
                # percent within [kpi_min, kpi_max]
                lo = self.kpi_min if self.kpi_min is not None else 0.0
                hi = self.kpi_max if self.kpi_max is not None else 0.0
                span = float(hi - lo)
                pct = 0
                try:
                    if span > 0:
                        pct = int(max(0.0, min(100.0, ((float(cur) - float(lo)) / span) * 100.0)))
                except Exception:  # noqa: BLE001
                    pct = 0
                self.current_percent = pct
                # color based on QC thresholds (green/yellow/red)
                cur_v = float(cur or 0.0)
                cmin = self.qc_min if self.qc_min is not None else None
                cmax = self.qc_max if self.qc_max is not None else None
                color = "#10b981"  # green
                try:
                    if cmin is not None and cmax is not None and cmax > cmin:
                        warn_band = 0.05 * (cmax - cmin)
                        if cur_v < cmin or cur_v > cmax:
                            color = "#ef4444"  # red
                        elif (cur_v - cmin) <= warn_band or (cmax - cur_v) <= warn_band:
                            color = "#f59e0b"  # yellow
                        else:
                            color = "#10b981"  # green
                    elif cmin is not None and cur_v < cmin:
                        color = "#ef4444"
                    elif cmax is not None and cur_v > cmax:
                        color = "#ef4444"
                except Exception:
                    color = "#10b981"
                self.current_color = color
                # segmented track css (grafana-like)
                try:
                    min_pct = 0.0
                    max_pct = 100.0
                    if span > 0:
                        if self.qc_min is not None:
                            min_pct = max(0.0, min(100.0, ((float(self.qc_min) - float(lo)) / span) * 100.0))
                        if self.qc_max is not None:
                            max_pct = max(0.0, min(100.0, ((float(self.qc_max) - float(lo)) / span) * 100.0))
                    warn = 5.0
                    y1 = min(100.0, min_pct + warn)
                    y2 = max(0.0, max_pct - warn)
                    self.gauge_track_css = (
                        f"conic-gradient(#ef4444 0 {min_pct}%, #f59e0b {min_pct}% {y1}%, "
                        f"#10b981 {y1}% {y2}%, #f59e0b {y2}% {max_pct}%, #e5e7eb {max_pct}% 100%)"
                    )
                except Exception:
                    self.gauge_track_css = "conic-gradient(#e5e7eb 0 100%)"
        except Exception as e:  # noqa: BLE001
            # 🔧 오류 처리 개선: 적절한 로깅으로 교체
            import logging
            logging.error(f"🚨 load() 함수 오류 발생: {type(e).__name__}: {e}", exc_info=True)
            async with self:
                self.error = f"데이터 로딩 실패: {type(e).__name__}: {str(e)}"
                # 오류 발생시에도 기본 데이터 구조 초기화
                if not hasattr(self, 'kpi_rows') or self.kpi_rows is None:
                    self.kpi_rows = []
                if not hasattr(self, 'series') or self.series is None:
                    self.series = []
                if not hasattr(self, 'tags') or self.tags is None:
                    self.tags = []
                # 🔧 오류 처리 개선: 적절한 로깅으로 교체
                import logging
                logging.info("🔧 오류 복구: 기본 데이터 구조 초기화 완료")
        finally:
            # 🔧 개발용 디버그 메시지를 로깅으로 변경
            import logging
            logging.debug("🔍 load() 함수 완료 - 로딩 상태 False로 설정")
            async with self:
                self.loading = False
                
        # 로드 완료 후 실시간 모드가 활성화되어 있고 아직 루프가 실행 중이 아니면 시작
        print(f"🔍 페이지 로드 완료 - 실시간 모드: {self.realtime_mode}, 루프 실행 중: {self._realtime_loop_running}")
        
        # 🔧 싱글톤 패턴 실시간 루프 관리: 메인 페이지에서만 시작
        try:
            current_path = self.router.url.path
        except:
            current_path = "/"
            
        is_main_page = (current_path == "/")
        
        if self.realtime_mode and not self._realtime_loop_running and is_main_page:
            print(f"🚀 메인 페이지 로드 완료 - 실시간 모드 시작")
            return DashboardState.start_realtime
        elif self.realtime_mode and self._realtime_loop_running:
            print(f"✅ 페이지 로드 완료 - 실시간 루프 이미 실행 중 (ID: {self._realtime_loop_id})")
        elif self.realtime_mode and not is_main_page:
            print(f"🔄 페이지 로드 완료 - 메인 페이지가 아니므로 실시간 루프 시작 스킵 (경로: {current_path})")
        else:
            print(f"⚠️ 페이지 로드 완료 - 실시간 모드가 비활성화됨")

    @rx.event
    def toggle_overlay(self, value: object):
        s = str(value).strip().lower()
        self.overlay_enabled = s in {"true", "1", "on", "checked", "yes"}

    @rx.event
    def set_tag_select(self, value: str):
        """Coerce empty selection to None for SQL filter."""
        self.tag_name = value or None

    @rx.event
    def set_window(self, value: str):
        self.range_mode = "relative"
        self.window = value or "5 min"
        # 요구 정책 매핑
        wl = (self.window or "").lower()
        if wl in {"1 min", "5 min", "10 min", "60 min"}:
            self.resolution = "1m"
        elif wl in {"12 hour", "24 hour", "48 hour"}:
            self.resolution = "10m"
        elif wl in {"7 days", "14 days", "30 days"}:
            self.resolution = "1h"
        elif wl in {"3 months", "6 months", "12 months"}:
            self.resolution = "1d"
        else:
            # fallback
            if "minute" in wl:
                self.resolution = "1m"
            elif "hour" in wl:
                self.resolution = "10m"
            elif "day" in wl:
                self.resolution = "1h"
            else:
                self.resolution = "1h"

    # removed absolute picker handlers and apply logic

    @rx.event
    async def reload(self):
        return type(self).load

    async def get_mini_chart_data(self, tag_name: str, hours: int = 6) -> List[Dict[str, Any]]:
        """Get mini chart data for KPI cards - last N hours with 1-minute resolution"""
        try:
            data = await timeseries(
                tag_name=tag_name,
                window=f"{hours} hours",
                resolution="1m"
            )
            
            chart_data = []
            for row in data[-24:]:
                if row.get("avg") is not None:
                    chart_data.append({
                        "bucket": _fmt_ts_short(row.get("bucket")),
                        "avg": _to_float(row.get("avg")) or 0
                    })
            
            return chart_data
            
        except Exception as e:
            # 🔧 오류 처리 개선: 적절한 로깅으로 교체
            import logging
            logging.error(f"미니 차트 데이터 조회 실패 - tag_name: {tag_name}, 오류: {e}", exc_info=True)
            return []

    def _parse_abs(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        return None, None

    @rx.event
    def set_quick_range(self, minutes: int):
        # quick ranges are relative; clear absolute inputs
        self.range_mode = "relative"
        self.abs_from_s = ""
        self.abs_to_s = ""
        if minutes < 60:
            self.window = f"{minutes} minutes"
        elif minutes % 1440 == 0:
            self.window = f"{minutes // 1440} days"
        else:
            self.window = f"{minutes // 60} hours"
        return type(self).load

    @rx.event
    def use_recent(self, idx: int):
        return None

    @rx.event
    def set_resolution(self, value: str):
        self.resolution = value or None

    @rx.event
    def set_start_iso(self, value: str):
        self.start_iso = value or None

    @rx.event
    def set_end_iso(self, value: str):
        self.end_iso = value or None

    # ----- Chart series toggles -----
    @rx.event
    def set_show_avg(self, v: object):
        self.show_avg = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_min(self, v: object):
        self.show_min = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_max(self, v: object):
        self.show_max = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_last(self, v: object):
        self.show_last = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_first(self, v: object):
        self.show_first = str(v).lower() in {"true", "1", "on", "checked"}

    # Tech indicator checkbox setters
    @rx.event
    def set_show_tech_avg(self, v: object):
        self.show_tech_avg = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_sma_10(self, v: object):
        self.show_sma_10 = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_sma_60(self, v: object):
        self.show_sma_60 = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_bb_upper(self, v: object):
        self.show_bb_upper = str(v).lower() in {"true", "1", "on", "checked"}

    @rx.event
    def set_show_bb_lower(self, v: object):
        self.show_bb_lower = str(v).lower() in {"true", "1", "on", "checked"}

    # Chart view mode toggle functions
    @rx.event
    def toggle_chart_view_mode(self):
        """상위 토글: Area/Composed 전환"""
        self.chart_view_mode = not self.chart_view_mode

    @rx.event
    def set_trend_selected(self, value: str | list[str]):
        """Trend 그룹 토글 버튼 선택"""
        if isinstance(value, list):
            value = value[0] if value else "avg"
        self.trend_selected = value

    @rx.event
    def set_tech_selected(self, value: str | list[str]):
        """Tech 그룹 토글 버튼 선택"""
        if isinstance(value, list):
            value = value[0] if value else "avg"
        self.tech_selected = value

    @rx.event
    def set_trend_composed_selected(self, value: str | list[str]):
        """Trend Composed 모드 다중 선택 (세그먼트 컨트롤)"""
        if isinstance(value, str):
            self.trend_composed_selected = [value]
        else:
            self.trend_composed_selected = value

    @rx.event  
    def set_tech_composed_selected(self, value: str | list[str]):
        """Tech Composed 모드 다중 선택 (세그먼트 컨트롤)"""
        if isinstance(value, str):
            self.tech_composed_selected = [value]
        else:
            self.tech_composed_selected = value

    # Legacy chart toggle functions (for composed mode)
    @rx.event
    def toggle_trend_chart(self):
        self.trend_chart_toggle = not self.trend_chart_toggle

    @rx.event
    def toggle_tech_chart(self):
        self.tech_chart_toggle = not self.tech_chart_toggle

    @rx.event(background=True)
    async def start_auto(self):
        # 주기적으로 로드. 로딩 중이면 스킵하여 중복 방지
        while self.auto_refresh:
            if not self.loading:
                # 클래스 참조 이벤트로 반환 (Reflex 요구 사항)
                yield DashboardState.load
            await asyncio.sleep(self.auto_interval_s)

    @rx.event
    def stop_auto(self):
        self.auto_refresh = False

    @rx.event
    def refresh(self):
        self.reload_token += 1
        return type(self).load
    
    @rx.event
    def toggle_auto_refresh(self):
        """자동 새로고침 토글"""
        self.auto_refresh = not self.auto_refresh
        if self.auto_refresh:
            # 🔧 일관성 수정: 데코레이터가 있는 start_auto 메서드 사용
            return type(self).start_auto
        # 새로고침 중지시에는 단순히 상태만 변경 (start_auto 루프가 자동 종료됨)
        return
    
    @rx.event
    def set_auto_interval(self, interval: str):
        """자동 새로고침 간격 설정"""
        try:
            self.auto_interval_s = int(interval)
        except ValueError:
            self.auto_interval_s = 15
    
    # 🧹 중복 메서드 제거: start_auto 메서드로 통일됨
    
    # 실시간 모드 메소드들
    @rx.event
    def toggle_realtime_mode(self):
        """실시간 모드 토글"""
        self.realtime_mode = not self.realtime_mode
        if self.realtime_mode and not self._realtime_loop_running:
            return DashboardState.start_realtime
        elif not self.realtime_mode:
            return DashboardState.stop_realtime
    
    @rx.event(background=True)
    async def start_realtime(self):
        """실시간 데이터 수집 시작 - 10초마다 업데이트 (싱글톤 패턴)"""
        import time
        import uuid
        
        # 싱글톤 패턴: 실행 전 이중 체크와 잠금
        async with self:
            current_time = time.strftime("%H:%M:%S")
            
            # 이미 실행 중이면 완전 차단
            if self._realtime_loop_running:
                print(f"🚫 {current_time} - 싱글톤 보호: 실시간 루프가 이미 실행 중 (ID: {self._realtime_loop_id})")
                return
                
            # 실시간 모드가 꺼져있으면 시작하지 않음
            if not self.realtime_mode:
                print(f"⚠️ {current_time} - 실시간 모드가 비활성화되어 루프 시작 취소")
                return
                
            # 새 루프 ID 생성 및 상태 업데이트 (원자적 연산)
            loop_id = str(uuid.uuid4())[:8]
            self._realtime_loop_id = loop_id
            self._realtime_loop_running = True
            print(f"🔒 {current_time} - 싱글톤 루프 잠금 설정 완료 [ID:{loop_id}]")
            
        start_time = time.strftime("%H:%M:%S")
        print(f"🚀 {start_time} - 실시간 모드 시작 [ID:{loop_id}] (간격: {self.realtime_interval_s}초)")
        
        try:
            loop_count = 0
            while self.realtime_mode and self._realtime_loop_running and self._realtime_loop_id == loop_id:
                try:
                    await asyncio.sleep(self.realtime_interval_s)
                    
                    # 루프 상태 재확인 (다른 루프가 시작되었거나 중단되었을 수 있음)
                    if not self.realtime_mode or not self._realtime_loop_running or self._realtime_loop_id != loop_id:
                        break
                        
                    loop_count += 1
                    current_time = time.strftime("%H:%M:%S")
                    print(f"🔄 {current_time} - [{loop_id}] 실시간 업데이트 #{loop_count}")
                    yield DashboardState.update_realtime_data
                    
                except Exception as e:
                    print(f"❌ [{loop_id}] 실시간 업데이트 오류: {e}")
                    break
                    
        finally:
            # 루프 종료 시 상태 정리 (메모리 누수 방지)
            async with self:
                if self._realtime_loop_id == loop_id:  # 이 루프가 여전히 활성 루프인 경우만 정리
                    self._realtime_loop_running = False
                    self._realtime_loop_id = None
                    print(f"🧹 [{loop_id}] 루프 상태 정리 완료")
                else:
                    print(f"🔄 [{loop_id}] 다른 루프가 활성화되어 상태 정리 스킵")
                    
            end_time = time.strftime("%H:%M:%S")
            print(f"⏹️ {end_time} - [{loop_id}] 실시간 루프 종료 (총 {loop_count}회 실행)")
    
    @rx.event
    def stop_realtime(self):
        """실시간 데이터 수집 중지"""
        import time
        stop_time = time.strftime("%H:%M:%S")
        loop_id = self._realtime_loop_id
        print(f"🛑 {stop_time} - 실시간 모드 중지 요청 (현재 루프 ID: {loop_id})")
        
        # 실시간 모드와 루프 상태 모두 중지
        self.realtime_mode = False
        self._realtime_loop_running = False
        # loop_id는 실제 루프에서 정리하도록 유지
    
    @rx.event(background=True)
    async def update_realtime_data(self):
        """실시간 데이터 업데이트 (부분 업데이트)"""
        try:
            # 업데이트 조건 체크: 대시보드 페이지에서만 실시간 업데이트
            try:
                current_path = self.router.url.path
            except:
                # fallback - 모든 페이지에서 실시간 업데이트 허용
                current_path = "/"
            
            # 트렌드 페이지와 기술지표 페이지에서는 실시간 업데이트 스킵
            if not self.loading and self.realtime_mode and current_path in ["/trend", "/tech"]:
                print(f"🛑 현재 경로: {current_path} - 실시간 업데이트 스킵")
                return
            elif not self.loading and self.realtime_mode:
                print(f"🎯 현재 경로: {current_path} - 실시간 업데이트 실행")
            
            if not self.loading and self.realtime_mode:
                import time
                current_time = time.strftime("%H:%M:%S")
                
                # influx_hist에서 모든 태그의 5초 간격 실시간 데이터 가져오기
                from ...queries.realtime import get_all_tags_latest_realtime
                
                # 모든 태그의 5초 간격 최신 실시간 데이터 가져오기
                realtime_data = await get_all_tags_latest_realtime()
                if realtime_data and len(realtime_data) > 0:
                    async with self:
                        # KPI 카드 데이터를 influx_hist 실시간 데이터 기반으로 통합 업데이트
                        self._update_kpi_unified_from_realtime(realtime_data)
                        
                        # 시리즈 데이터에도 최신 실시간 데이터를 추가 (큰 차트용)
                        self._update_series_with_realtime(realtime_data)
                    
                    print(f"📊 {current_time} - 실시간 데이터 기반 KPI+차트 통합 업데이트 완료 ({len(realtime_data)}개 태그)")
                    
                    # UI 업데이트를 위한 yield 추가
                    yield
                else:
                    print(f"⚠️ {current_time} - influx_hist 실시간 데이터 없음")
                        
        except Exception as e:
            async with self:
                self.error = f"실시간 데이터 업데이트 오류: {str(e)}"
            # 🔧 오류 처리 개선: 적절한 로깅으로 교체
            import logging
            logging.error(f"❌ 실시간 업데이트 실패: {str(e)}", exc_info=True)
            yield
    
    def _update_kpi_latest_values(self, latest_data):
        """기존 KPI 행들의 최신값만 업데이트 (차트/통계 데이터는 유지)"""
        try:
            if not self.kpi_rows or not latest_data:
                return
                
            # latest_data를 tag_name으로 인덱싱
            latest_by_tag = {}
            for row in latest_data:
                tag_name = row.get("tag_name")
                if tag_name:
                    latest_by_tag[tag_name] = row
            
            # 기존 kpi_rows의 최신값과 타임스탬프만 업데이트
            updated_rows = []
            for kpi_row in self.kpi_rows:
                updated_row = dict(kpi_row)  # 기존 데이터 복사
                tag_name = kpi_row.get("tag_name")
                
                if tag_name in latest_by_tag:
                    latest_row = latest_by_tag[tag_name]
                    value = latest_row.get("value")
                    ts = latest_row.get("ts")
                    
                    if value is not None:
                        # 최신값과 시간 업데이트 (다른 필드는 유지)
                        updated_row["value_s"] = f"{float(value):.2f}"
                        updated_row["last_s"] = f"{float(value):.2f}"
                        if ts:
                            # 기존 _fmt_ts_short 함수 사용 (년월일 포함)
                            updated_row["ts_s"] = _fmt_ts_short(str(ts))
                
                updated_rows.append(updated_row)
            
            self.kpi_rows = updated_rows
            
        except Exception as e:
            # 🔧 오류 처리 개선: 적절한 로깅으로 교체
            import logging
            logging.error(f"KPI 최신값 업데이트 실패: {e}", exc_info=True)
    
    def _update_kpi_from_realtime(self, latest_point):
        """실시간 데이터 포인트로 KPI 업데이트"""
        try:
            if not self.kpi_rows or not latest_point:
                return
                
            tag_name = latest_point.get("tag_name")
            value = latest_point.get("value")
            timestamp_iso = latest_point.get("timestamp")
            
            if not tag_name or value is None:
                return
                
            # 해당 태그의 KPI 행 찾아서 업데이트
            updated_rows = []
            for kpi_row in self.kpi_rows:
                updated_row = dict(kpi_row)  # 기존 데이터 복사
                
                if kpi_row.get("tag_name") == tag_name:
                    # 실시간 데이터로 값과 시간 업데이트
                    updated_row["value_s"] = f"{float(value):.2f}"
                    updated_row["last_s"] = f"{float(value):.2f}"
                    if timestamp_iso:
                        updated_row["ts_s"] = _fmt_ts_short(timestamp_iso)
                
                updated_rows.append(updated_row)
            
            self.kpi_rows = updated_rows
            
        except Exception as e:
            # 🔧 오류 처리 개선: 적절한 로깅으로 교체
            import logging
            logging.error(f"실시간 KPI 업데이트 실패: {e}", exc_info=True)
    
    def _update_kpi_unified_from_realtime(self, realtime_data):
        """influx_hist 5초 간격 실시간 데이터로 KPI 카드의 모든 정보를 통합 업데이트"""
        try:
            if not self.kpi_rows or not realtime_data:
                return
                
            # realtime_data를 tag_name으로 인덱싱
            realtime_by_tag = {}
            for row in realtime_data:
                tag_name = row.get("tag_name")
                if tag_name:
                    realtime_by_tag[tag_name] = row
            
            # QC 규칙 데이터 가져오기 (기존 방식 유지)
            qc_by_tag = {}
            for qc_row in (self.qc or []):
                tag_name = qc_row.get("tag_name")
                if tag_name:
                    qc_by_tag[tag_name] = qc_row
            
            # 기존 kpi_rows를 실시간 데이터 기반으로 통합 업데이트
            updated_rows = []
            for kpi_row in self.kpi_rows:
                updated_row = dict(kpi_row)  # 기존 데이터 복사
                tag_name = kpi_row.get("tag_name")
                
                if tag_name in realtime_by_tag:
                    realtime_row = realtime_by_tag[tag_name]
                    current_value = realtime_row.get("value")
                    current_ts = realtime_row.get("ts")
                    
                    if current_value is not None and current_ts:
                        # 1. 기본 값과 타임스탬프 업데이트
                        updated_row["value_s"] = f"{float(current_value):.2f}"
                        updated_row["last_s"] = f"{float(current_value):.2f}"
                        updated_row["ts_s"] = _fmt_ts_short(str(current_ts))

                        # 2. 변화율 계산 (기존 값과 비교)
                        prev_value = kpi_row.get("last_s")
                        if prev_value and prev_value != "Error":
                            try:
                                prev_val = float(prev_value.replace(" ", ""))
                                delta_pct = ((float(current_value) - prev_val) / prev_val) * 100
                                updated_row["delta_pct"] = round(delta_pct, 2)
                                updated_row["delta_s"] = f"{delta_pct:+.2f}%"
                            except:
                                updated_row["delta_pct"] = 0.0
                                updated_row["delta_s"] = "0.00%"
                        else:
                            updated_row["delta_pct"] = 0.0
                            updated_row["delta_s"] = "0.00%"
                        
                        # 3. QC 기반 게이지와 상태 계산
                        qc_rule = qc_by_tag.get(tag_name, {})
                        def _fv(x):
                            try:
                                return float(x) if x is not None else None
                            except Exception:
                                return None
                        warn_min = _fv(qc_rule.get("warn_min"))
                        warn_max = _fv(qc_rule.get("warn_max"))
                        crit_min = _fv(qc_rule.get("crit_min"))
                        crit_max = _fv(qc_rule.get("crit_max"))
                        hard_min = _fv(qc_rule.get("min_val"))
                        hard_max = _fv(qc_rule.get("max_val"))
                        
                        # 게이지 퍼센트 계산 (기존 load 함수와 동일한 로직)
                        gauge_pct = 50.0  # 기본값
                        try:
                            # QC 범위가 있으면 QC 기준으로 계산
                            if (
                                current_value is not None and
                                hard_min is not None and
                                hard_max is not None and
                                hard_max > hard_min
                            ):
                                pos = (float(current_value) - hard_min) / (hard_max - hard_min)
                                gauge_pct = max(0.0, min(100.0, pos * 100.0))
                            # QC 범위가 없으면 절대값 기준 계산 (기본 로직)
                            elif current_value is not None:
                                if float(current_value) >= 0:
                                    gauge_pct = min(100.0, abs(float(current_value)) / 200.0 * 100.0)
                                else:
                                    gauge_pct = max(0.0, 100.0 - abs(float(current_value)) / 50.0 * 100.0)
                        except Exception:
                            gauge_pct = 50.0  # 오류 시 기본값
                        updated_row["gauge_pct"] = round(gauge_pct, 1)
                        
                        # 상태 레벨 계산 (기존 load 함수와 동일한 로직)
                        status_level = 0  # 기본: 정상
                        curr_val = float(current_value)
                        
                        # QC 규칙 기반 상태 계산
                        if (hard_min is not None and curr_val < hard_min) or (hard_max is not None and curr_val > hard_max):
                            status_level = 2  # 위험
                        elif (crit_min is not None and curr_val < crit_min) or (crit_max is not None and curr_val > crit_max):
                            status_level = 2  # 위험
                        elif (warn_min is not None and curr_val < warn_min) or (warn_max is not None and curr_val > warn_max):
                            status_level = 1  # 경고
                        
                        # 추가 조건 (QC 규칙이 없는 경우)
                        if status_level == 0:
                            # 특별 케이스: 음수값은 항상 위험 (최우선)
                            if curr_val < 0:
                                status_level = 2
                            elif gauge_pct >= 90:  # 90% 이상 → 위험 (빨강)
                                status_level = 2
                            elif gauge_pct >= 70:  # 70% 이상 → 경고 (노랑)
                                status_level = 1
                            
                        updated_row["status_level"] = status_level
                        
                        # 4. QC 범위 라벨 업데이트
                        if hard_min is not None and hard_max is not None:
                            updated_row["range_label"] = f"{hard_min:.2f} ~ {hard_max:.2f}"
                        else:
                            updated_row["range_label"] = "범위 없음"
                        
                        # 5. 통신 상태 (실시간 데이터가 있으면 정상)
                        updated_row["comm_status"] = True
                        updated_row["comm_text"] = "OK"
                
                updated_rows.append(updated_row)
            
            # 전체 KPI 데이터와 latest 데이터도 업데이트
            self.kpi_rows = updated_rows
            self.latest = realtime_data
            
            # 실시간 차트 데이터 업데이트 (각 태그별로)
            updated_realtime_data = {}
            for realtime_row in realtime_data:
                tag_name = realtime_row.get("tag_name")
                current_value = realtime_row.get("value")
                current_ts = realtime_row.get("ts")
                
                if tag_name and current_value is not None and current_ts:
                    # 기존 실시간 데이터 가져오기 (최대 12개 포인트 유지)
                    existing_data = self.realtime_data.get(tag_name, [])
                    
                    # 새 데이터 포인트 생성
                    new_point = {
                        "bucket": _fmt_ts_time_only(str(current_ts)),
                        "value": float(current_value),
                        "ts": str(current_ts)
                    }
                    
                    # 중복 타임스탬프 방지: 마지막 데이터와 동일한 시간이면 건너뛰기
                    if existing_data and existing_data[-1].get("ts") == str(current_ts):
                        continue  # 이미 동일한 시간의 데이터가 있으므로 스킨
                    
                    # 새 데이터를 추가하고 최근 6개만 유지 (1분간 10초 간격)
                    updated_data = existing_data + [new_point]
                    updated_realtime_data[tag_name] = updated_data[-6:]  # 최근 6개만 유지
            
            # 실시간 차트 데이터 업데이트
            if updated_realtime_data:
                self.realtime_data.update(updated_realtime_data)
                
            # KPI 행들의 실시간 차트 데이터도 업데이트
            for i, kpi_row in enumerate(self.kpi_rows):
                tag_name = kpi_row.get("tag_name")
                if tag_name in updated_realtime_data:
                    self.kpi_rows[i]["realtime_chart_data"] = updated_realtime_data[tag_name]
            
        except Exception as e:
            # 🔧 오류 처리 개선: 적절한 로깅으로 교체
            import logging
            logging.error(f"KPI 통합 업데이트 실패: {e}", exc_info=True)
    
    def _update_series_with_realtime(self, realtime_data):
        """시리즈 데이터에 실시간 데이터를 추가하여 큰 차트 업데이트"""
        try:
            if not realtime_data:
                return
                
            import time
            from datetime import datetime, timezone
                
            # 현재 시간을 새로운 버킷으로 사용
            current_time = datetime.now(timezone.utc)
            bucket_str = current_time.isoformat()
            
            # realtime_data를 tag_name으로 인덱싱
            realtime_by_tag = {}
            for row in realtime_data:
                tag_name = row.get("tag_name")
                if tag_name:
                    realtime_by_tag[tag_name] = row
            
            # 기존 시리즈 데이터에 새 실시간 포인트 추가
            updated_series = list(self.series or [])
            
            for tag_name, realtime_row in realtime_by_tag.items():
                current_value = realtime_row.get("value")
                if current_value is not None:
                    # 새 시리즈 데이터 포인트 생성
                    new_point = {
                        "bucket": bucket_str,
                        "bucket_formatted": _fmt_ts_short_chart(bucket_str),
                        "tag_name": tag_name,
                        "avg": float(current_value),
                        "min": float(current_value),
                        "max": float(current_value), 
                        "last": float(current_value),
                        "first": float(current_value),
                        "n": 1,
                        # formatted strings
                        "avg_s": _fmt_s(float(current_value), 2),
                        "min_s": _fmt_s(float(current_value), 2),
                        "max_s": _fmt_s(float(current_value), 2),
                        "last_s": _fmt_s(float(current_value), 2),
                        "first_s": _fmt_s(float(current_value), 2),
                        "n_s": "1",
                    }
                    
                    updated_series.append(new_point)
            
            # 시리즈 데이터가 너무 많아지지 않도록 제한 (최근 1000개 포인트만 유지)
            if len(updated_series) > 1000:
                updated_series = updated_series[-1000:]
                
            # 시간 순으로 정렬
            updated_series.sort(key=lambda r: ((r.get("tag_name") or ""), (r.get("bucket") or "")))
            
            self.series = updated_series
            
        except Exception as e:
            # 🔧 오류 처리 개선: 적절한 로깅으로 교체
            import logging
            logging.error(f"시리즈 데이터 업데이트 실패: {e}", exc_info=True)
    
    @rx.var
    def get_realtime_chart_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """현재 실시간 차트 데이터 반환"""
        return self.realtime_data
    
    # 세그먼트 컨트롤 연동을 위한 computed properties
    @rx.var
    def show_trend_min(self) -> bool:
        """Trend Composed 차트에서 min 라인 표시 여부"""
        return "min" in self.trend_composed_selected
    
    @rx.var  
    def show_trend_max(self) -> bool:
        """Trend Composed 차트에서 max 라인 표시 여부"""
        return "max" in self.trend_composed_selected
        
    @rx.var
    def show_trend_first(self) -> bool:
        """Trend Composed 차트에서 first 라인 표시 여부"""
        return "first" in self.trend_composed_selected
        
    @rx.var
    def show_trend_last(self) -> bool:
        """Trend Composed 차트에서 last 라인 표시 여부"""
        return "last" in self.trend_composed_selected
        
    @rx.var
    def show_tech_sma_10(self) -> bool:
        """Tech Composed 차트에서 SMA 10 라인 표시 여부"""
        return "sma_10" in self.tech_composed_selected
        
    @rx.var
    def show_tech_sma_60(self) -> bool:
        """Tech Composed 차트에서 SMA 60 라인 표시 여부"""
        return "sma_60" in self.tech_composed_selected
        
    @rx.var
    def show_tech_bb_upper(self) -> bool:
        """Tech Composed 차트에서 BB Upper 라인 표시 여부"""
        return "bb_upper" in self.tech_composed_selected
        
    @rx.var
    def show_tech_bb_lower(self) -> bool:
        """Tech Composed 차트에서 BB Lower 라인 표시 여부"""
        return "bb_lower" in self.tech_composed_selected
    
    def get_tag_realtime_data(self, tag_name: str) -> List[Dict[str, Any]]:
        """특정 태그의 실시간 데이터 반환"""
        return self.realtime_data.get(tag_name, [])
    
    @rx.event
    def navigate_to_detail(self, tag_name: str):
        """DETAIL 버튼 클릭 시 해당 센서의 상세 페이지로 이동"""
        self.tag_name = tag_name
        return rx.redirect("/detail")
    
    @rx.event
    def open_detail_modal(self, tag_name: str):
        """DETAIL 모달 열기"""
        # 해당 센서 데이터 찾기
        for row in self.kpi_rows:
            if row.get("tag_name") == tag_name:
                self.selected_sensor_data = dict(row)
                break
        self.detail_modal_open = True
    
    @rx.event 
    def close_detail_modal(self):
        """DETAIL 모달 닫기"""
        self.detail_modal_open = False
        self.selected_sensor_data = {}
    
    @rx.event
    def toggle_sidebar(self):
        """사이드바 접기/펼치기 토글"""
        self.sidebar_collapsed = not self.sidebar_collapsed

