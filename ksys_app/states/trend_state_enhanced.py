"""
Enhanced Trend State with Hierarchical Tag Selection
Based on successful dashboard pattern with Station/System/Tag hierarchy
"""
import reflex as rx
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta, timezone
import asyncio
from reflex.utils import console
from ..db_orm import get_async_session
from ..services.trend_service import TrendService
from .tag_hierarchy_state import TagHierarchyState


class TrendStateEnhanced(TagHierarchyState):
    """Enhanced trend page State with hierarchical tag selection"""

    # 기본 상태
    loading: bool = False
    error: Optional[str] = None

    # 차트 데이터
    series: List[Dict[str, Any]] = []

    # 집계 설정
    aggregation_view: str = "10m"  # 1m, 10m, 1h, 1d
    time_range: str = "24 hours"  # 내부 value (hours 단위)
    time_range_display: str = "최근 1일"  # 화면 표시용
    time_range_options: List[Dict[str, str]] = [
        {"label": "최근 1일", "value": "24 hours"},
        {"label": "최근 3일", "value": "72 hours"},
        {"label": "최근 7일", "value": "168 hours"},
        {"label": "최근 14일", "value": "336 hours"},
        {"label": "최근 30일", "value": "720 hours"},
    ]  # 10m의 기본 옵션

    # 차트 모드
    chart_mode: str = "area"  # area, line, bar, composed
    trend_selected: str = "last"
    trend_composed_selected: List[str] = ["last"]

    # Y축 스케일 설정
    auto_scale: bool = False  # False: domain=["dataMin - 5", "dataMax + 5"], True: domain=["auto", "auto"]

    # 자동 새로고침 설정
    auto_refresh: bool = False
    refresh_interval: int = 30  # seconds

    # 페이지네이션 설정
    page: int = 1  # 현재 페이지 (1-based)
    page_size: int = 20  # 페이지당 행 수
    total_pages: int = 1  # 총 페이지 수

    @rx.event(background=True)
    async def load(self):
        """페이지 로드 시 초기 데이터 가져오기"""
        console.log("🔄 TrendStateEnhanced.load() called")

        # Load tag hierarchy first
        if not self.is_hierarchy_loaded:
            yield TrendStateEnhanced.load_tag_hierarchy

        async with self:
            self.loading = True
            self.error = None
            yield

        try:
            # If we have selected tags from hierarchy, use the first one
            if self.selected_tags:
                async with self:
                    console.log(f"📌 Using selected tag from hierarchy: {self.selected_tags[0]}")
                    yield
                # Load data for selected tag
                yield TrendStateEnhanced.load_series_data
            elif self.all_tags:
                # Select first available tag if none selected
                async with self:
                    self.selected_tags = [self.all_tags[0]]
                    console.log(f"📌 Auto-selected first tag: {self.selected_tags[0]}")
                    yield
                yield TrendStateEnhanced.load_series_data

        except Exception as e:
            async with self:
                self.error = f"데이터 로드 실패: {str(e)}"
            console.error(f"❌ TrendStateEnhanced.load error: {e}")
        finally:
            async with self:
                self.loading = False
            console.log("🏁 TrendStateEnhanced.load() completed")

    @rx.event(background=True)
    async def load_series_data(self):
        """선택된 태그의 시계열 데이터 로드"""
        # Get first selected tag
        if not self.selected_tags:
            console.log("⚠️ No tags selected")
            return

        tag_name = self.selected_tags[0]
        time_range = self.time_range
        aggregation_view = self.aggregation_view

        async with self:
            self.loading = True
            yield

        try:
            # Parse time range
            hours = self._parse_time_range(time_range)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)

            # Get aggregation table
            table_name = self._get_aggregation_table(aggregation_view)

            # Load data using service
            async with get_async_session() as session:
                service = TrendService(session)
                series_data = await service.get_series_data(
                    tag_name=tag_name,
                    start_time=start_time,
                    end_time=end_time,
                    aggregation_table=table_name,
                    max_points=5000
                )

            async with self:
                self.series = series_data
                self.loading = False
                console.log(f"📊 Loaded {len(series_data)} data points for {tag_name}")
                yield

        except Exception as e:
            async with self:
                self.error = f"데이터 로드 실패: {str(e)}"
                self.loading = False
            console.error(f"❌ TrendStateEnhanced.load_series_data error: {e}")

    @rx.event(background=True)
    async def on_tag_selected(self, tag: str):
        """태그 선택 이벤트 - hierarchical_tag_selector에서 호출"""
        async with self:
            # Update selected_tags from hierarchy selector
            if tag not in self.selected_tags:
                self.selected_tags = [tag]  # For trend, we only use single selection
            console.log(f"📌 Tag selected: {tag}")
            yield
        # Load data for newly selected tag
        yield TrendStateEnhanced.load_series_data

    @rx.event(background=True)
    async def on_tag_removed(self, tag: str):
        """태그 제거 이벤트 - hierarchical_tag_selector에서 호출"""
        async with self:
            self.selected_tags = [t for t in self.selected_tags if t != tag]
            console.log(f"❌ Tag removed: {tag}")
            yield
        # If no tags left, don't load data
        if self.selected_tags:
            yield TrendStateEnhanced.load_series_data

    @rx.event(background=True)
    async def set_aggregation_view(self, value: str):
        """집계 뷰 설정"""
        console.log(f"🔄 set_aggregation_view called with: {value}")

        # Get new options outside async with self
        new_options = self._get_time_range_options(value)
        console.log(f"📋 New time range options: {[opt['label'] for opt in new_options]}")

        async with self:
            self.aggregation_view = value
            self.time_range_options = new_options
            # Set first option for each aggregation unit
            if self.time_range_options:
                self.time_range = self.time_range_options[0]["value"]
                self.time_range_display = self.time_range_options[0]["label"]
                console.log(f"✅ Set time_range to: {self.time_range_display}")
            yield
        yield TrendStateEnhanced.load_series_data

    @rx.event(background=True)
    async def set_time_range(self, label: str):
        """시간 범위 설정 - 레이블을 받아서 value로 변환"""
        console.log(f"🔄 set_time_range called with: {label}")

        # Find actual value from label
        actual_value = label  # default
        display_label = label
        for opt in self.time_range_options:
            if opt["label"] == label:
                actual_value = opt["value"]
                display_label = opt["label"]
                console.log(f"✅ Found value for label '{label}': {actual_value}")
                break

        async with self:
            self.time_range = actual_value
            self.time_range_display = display_label
            yield
        yield TrendStateEnhanced.load_series_data

    @rx.event
    def set_chart_mode(self, mode: Union[str, List[str]]):
        """차트 모드 설정"""
        if isinstance(mode, list):
            self.chart_mode = mode[0] if mode else "area"
        else:
            self.chart_mode = mode

    @rx.event
    def set_trend_selected(self, value: Union[str, List[str]]):
        """Trend 선택"""
        if isinstance(value, list):
            self.trend_selected = value[0] if value else "last"
        else:
            self.trend_selected = value

    @rx.event
    def toggle_auto_scale(self):
        """Y축 Auto scale 토글"""
        self.auto_scale = not self.auto_scale

    @rx.event
    def toggle_trend_composed_item(self, value: str):
        """Composed 모드 토글"""
        if value in self.trend_composed_selected:
            self.trend_composed_selected = [
                item for item in self.trend_composed_selected if item != value
            ]
        else:
            self.trend_composed_selected.append(value)

    @rx.event(background=True)
    async def toggle_auto_refresh(self):
        """자동 새로고침 토글"""
        async with self:
            self.auto_refresh = not self.auto_refresh
            yield

        if self.auto_refresh:
            yield TrendStateEnhanced.auto_refresh_loop

    @rx.event(background=True)
    async def auto_refresh_loop(self):
        """자동 새로고침 루프"""
        while True:
            # Check auto_refresh state
            if not self.auto_refresh:
                break

            # Wait for specified interval
            await asyncio.sleep(self.refresh_interval)

            # Still active?
            if self.auto_refresh:
                yield TrendStateEnhanced.load_series_data

    @rx.event
    def next_page(self):
        """다음 페이지로 이동"""
        if self.page < self.computed_total_pages:
            self.page += 1

    @rx.event
    def prev_page(self):
        """이전 페이지로 이동"""
        if self.page > 1:
            self.page -= 1

    @rx.event
    def set_page(self, page_num: int):
        """특정 페이지로 이동"""
        if 1 <= page_num <= self.computed_total_pages:
            self.page = page_num

    @rx.event
    def set_page_size(self, size: str):
        """페이지 크기 변경 및 첫 페이지로 이동"""
        self.page_size = int(size)
        self.page = 1  # 페이지 크기 변경 시 첫 페이지로 리셋

    @rx.event
    def export_csv_all(self):
        """전체 데이터 CSV 내보내기"""
        if not self.series_for_tag:
            return rx.window_alert("내보낼 데이터가 없습니다.")

        # Generate CSV data
        csv_lines = []
        csv_lines.append("No,Tag,Timestamp,Average,Min,Max,Last,First,Count")

        for row in self.series_for_tag_desc_with_num_all:
            csv_lines.append(
                f"{row.get('No', '')},"
                f"{row.get('Tag', '')},"
                f"{row.get('Timestamp', '')},"
                f"{row.get('Average', '')},"
                f"{row.get('Min', '')},"
                f"{row.get('Max', '')},"
                f"{row.get('Last', '')},"
                f"{row.get('First', '')},"
                f"{row.get('Count', '')}"
            )

        csv_content = "\n".join(csv_lines)
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        tag_name = self.selected_tags[0] if self.selected_tags else "unknown"
        filename = f"trend_{tag_name}_{self.aggregation_view}_{timestamp}_all.csv"

        return rx.download(
            data=csv_content.encode('utf-8-sig'),  # UTF-8 BOM for Excel
            filename=filename
        )

    @rx.event
    def export_csv_page(self):
        """현재 페이지만 CSV 내보내기"""
        if not self.series_for_tag:
            return rx.window_alert("내보낼 데이터가 없습니다.")

        # Generate CSV data
        csv_lines = []
        csv_lines.append("No,Tag,Timestamp,Average,Min,Max,Last,First,Count")

        for row in self.series_for_tag_desc_with_num:
            csv_lines.append(
                f"{row.get('No', '')},"
                f"{row.get('Tag', '')},"
                f"{row.get('Timestamp', '')},"
                f"{row.get('Average', '')},"
                f"{row.get('Min', '')},"
                f"{row.get('Max', '')},"
                f"{row.get('Last', '')},"
                f"{row.get('First', '')},"
                f"{row.get('Count', '')}"
            )

        csv_content = "\n".join(csv_lines)
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        tag_name = self.selected_tags[0] if self.selected_tags else "unknown"
        filename = f"trend_{tag_name}_{self.aggregation_view}_{timestamp}_page{self.page}.csv"

        return rx.download(
            data=csv_content.encode('utf-8-sig'),  # UTF-8 BOM for Excel
            filename=filename
        )

    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================

    @rx.var
    def current_tag_name(self) -> str:
        """현재 선택된 태그명 (첫 번째 태그)"""
        return self.selected_tags[0] if self.selected_tags else ""

    @rx.var
    def series_for_tag(self) -> List[Dict[str, Any]]:
        """선택된 태그의 시계열 데이터 - bucket 시간순으로 정렬"""
        tag_name = self.current_tag_name
        if tag_name:
            data = [r for r in self.series if r.get("tag_name") == tag_name]
        else:
            data = self.series or []

        # Sort by bucket timestamp to ensure X-axis is in chronological order
        if data and any(r.get("bucket") for r in data):
            data = sorted(data, key=lambda x: x.get("bucket") or datetime.min.replace(tzinfo=timezone.utc))

        return data

    @rx.var
    def series_count_s(self) -> str:
        """series_for_tag의 행 개수"""
        return str(len(self.series_for_tag or []))

    @rx.var
    def expected_data_count(self) -> int:
        """예상 데이터 개수 계산"""
        # 시간 범위와 집계 단위에 따른 예상 개수
        hours = self._parse_time_range(self.time_range)

        aggregation_minutes = {
            "1m": 1,
            "10m": 10,
            "1h": 60,
            "1d": 1440
        }

        interval_minutes = aggregation_minutes.get(self.aggregation_view, 10)
        total_minutes = hours * 60

        return int(total_minutes / interval_minutes)

    @rx.var
    def data_completeness(self) -> str:
        """데이터 완전성 비율 (%)"""
        expected = self.expected_data_count
        if expected == 0:
            return "0%"

        actual = len(self.series_for_tag or [])
        percentage = (actual / expected) * 100

        return f"{percentage:.2f}%"

    @rx.var
    def missing_data_count(self) -> int:
        """결측 데이터 개수"""
        expected = self.expected_data_count
        actual = len(self.series_for_tag or [])
        return max(0, expected - actual)

    @rx.var
    def data_average(self) -> str:
        """선택된 데이터의 평균값 - 기준선으로 사용 (문자열 반환)"""
        data = self.series_for_tag
        if not data:
            return "0"

        # Get the selected trend field
        field = self.trend_selected  # avg, min, max, first, last
        values = [float(row.get(field, 0)) for row in data if row.get(field) is not None]

        if not values:
            return "0"

        avg = sum(values) / len(values)
        return f"{avg:.2f}"

    @rx.var
    def time_range_labels(self) -> List[str]:
        """조회 기간 레이블들만 반환"""
        return [opt["label"] for opt in self.time_range_options]

    @rx.var
    def time_range_label(self) -> str:
        """현재 선택된 조회 기간의 레이블"""
        for opt in self.time_range_options:
            if opt["value"] == self.time_range:
                return opt["label"]
        return self.time_range  # Return value if no label found

    @rx.var
    def y_axis_domain(self) -> List[Union[float, str]]:
        """Y축 범위 계산 - auto_scale에 따라 동적 조정"""
        if self.auto_scale:
            return ["auto", "auto"]

        # Fixed scale: 데이터 min/max에서 ±5% 여유 추가
        data = self.series_for_tag
        if not data:
            return [0, 100]  # 기본값

        field = self.trend_selected  # avg, min, max, first, last
        values = [float(row.get(field, 0)) for row in data if row.get(field) is not None]

        if not values:
            return [0, 100]  # 기본값

        data_min = min(values)
        data_max = max(values)

        # ±5% 마진 추가
        margin = (data_max - data_min) * 0.05 if data_max != data_min else 10
        y_min = data_min - margin
        y_max = data_max + margin

        return [round(y_min, 2), round(y_max, 2)]

    @rx.var
    def series_for_tag_desc_with_num_all(self) -> List[Dict[str, Any]]:
        """테이블용 포맷팅된 전체 데이터 - 결측 시간대 포함 (페이지네이션 전)"""
        rows = list(self.series_for_tag or [])
        if not rows:
            return []

        # 집계 간격 (분)
        aggregation_minutes = {
            "1m": 1,
            "10m": 10,
            "1h": 60,
            "1d": 1440
        }
        interval_minutes = aggregation_minutes.get(self.aggregation_view, 10)

        # 시간 범위 계산
        hours = self._parse_time_range(self.time_range)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        # 예상되는 모든 버킷 생성 (역순)
        import pytz
        kst = pytz.timezone('Asia/Seoul')
        expected_buckets = []
        current_bucket = end_time

        while current_bucket > start_time:
            expected_buckets.append(current_bucket)
            current_bucket = current_bucket - timedelta(minutes=interval_minutes)

        # 버킷을 집계 간격으로 정규화하는 함수
        def normalize_bucket(dt: datetime, interval_minutes: int) -> datetime:
            """버킷 시간을 집계 간격으로 정규화 (초, 마이크로초 제거)"""
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            # 분을 집계 간격으로 내림
            normalized_minute = (dt.minute // interval_minutes) * interval_minutes
            return dt.replace(minute=normalized_minute, second=0, microsecond=0)

        # 실제 데이터를 딕셔너리로 변환 (정규화된 bucket을 키로)
        data_dict = {}
        for r in rows:
            if r.get("bucket"):
                bucket_time = r["bucket"]
                if bucket_time.tzinfo is None:
                    bucket_time = pytz.UTC.localize(bucket_time)
                normalized_bucket = normalize_bucket(bucket_time, interval_minutes)
                data_dict[normalized_bucket] = r

        # 예상 버킷과 실제 데이터 병합
        result = []
        tag_name = self.current_tag_name
        for idx, expected_bucket in enumerate(expected_buckets):
            # 예상 버킷도 정규화
            normalized_expected = normalize_bucket(expected_bucket, interval_minutes)

            # KST로 변환
            bucket_kst = normalized_expected.astimezone(kst)
            bucket_formatted = bucket_kst.strftime("%Y-%m-%d %H:%M:%S")

            # 실제 데이터가 있는지 확인 (정규화된 버킷으로)
            actual_data = data_dict.get(normalized_expected)

            if actual_data:
                # 데이터가 있으면 실제 값 표시
                result.append({
                    "No": str(idx + 1),
                    "Tag": str(actual_data.get("tag_name", "")),
                    "Timestamp": bucket_formatted,
                    "Average": f"{actual_data.get('avg', 0):.2f}" if actual_data.get('avg') else "0.00",
                    "Min": f"{actual_data.get('min', 0):.2f}" if actual_data.get('min') else "0.00",
                    "Max": f"{actual_data.get('max', 0):.2f}" if actual_data.get('max') else "0.00",
                    "Last": f"{actual_data.get('last', 0):.2f}" if actual_data.get('last') else "0.00",
                    "First": f"{actual_data.get('first', 0):.2f}" if actual_data.get('first') else "0.00",
                    "Count": str(actual_data.get("count") or actual_data.get("n") or 0),
                    "Missing": False
                })
            else:
                # 데이터가 없으면 결측 표시
                result.append({
                    "No": str(idx + 1),
                    "Tag": tag_name or "",
                    "Timestamp": bucket_formatted,
                    "Average": "—",  # em dash for missing
                    "Min": "—",
                    "Max": "—",
                    "Last": "—",
                    "First": "—",
                    "Count": "—",
                    "Missing": True
                })

        return result

    @rx.var
    def series_for_tag_desc_with_num(self) -> List[Dict[str, Any]]:
        """테이블용 포맷팅된 데이터 - 페이지네이션 적용"""
        all_data = self.series_for_tag_desc_with_num_all
        if not all_data:
            return []

        # 페이지 범위 계산
        start_idx = (self.page - 1) * self.page_size
        end_idx = start_idx + self.page_size

        return all_data[start_idx:end_idx]

    @rx.var
    def total_rows(self) -> int:
        """전체 행 수"""
        return len(self.series_for_tag_desc_with_num_all)

    @rx.var
    def computed_total_pages(self) -> int:
        """계산된 총 페이지 수"""
        if self.page_size <= 0:
            return 1
        total = self.total_rows
        return max(1, (total + self.page_size - 1) // self.page_size)  # 올림 처리

    @rx.var
    def page_info(self) -> str:
        """페이지 정보 문자열 (예: "1-20 / 144")"""
        total = self.total_rows
        if total == 0:
            return "0 / 0"

        start = (self.page - 1) * self.page_size + 1
        end = min(self.page * self.page_size, total)
        return f"{start}-{end} / {total}"

    @rx.var
    def has_prev_page(self) -> bool:
        """이전 페이지 존재 여부"""
        return self.page > 1

    @rx.var
    def has_next_page(self) -> bool:
        """다음 페이지 존재 여부"""
        return self.page < self.computed_total_pages

    def _parse_time_range(self, time_range: str) -> int:
        """시간 범위 문자열을 시간(hours)으로 변환"""
        parts = time_range.lower().split()
        if not parts:
            return 1

        try:
            value = int(parts[0])
            unit = parts[1] if len(parts) > 1 else "hour"

            if "hour" in unit:
                return value
            elif "day" in unit:
                return value * 24
            else:
                return 1
        except:
            return 1

    def _get_aggregation_table(self, view: str) -> str:
        """집계 뷰에 따른 테이블명 반환 - 보안 강화"""
        # SQL injection prevention with whitelist
        allowed_tables = {
            "1m": "influx_agg_1m",
            "10m": "influx_agg_10m",
            "1h": "influx_agg_1h",
            "1d": "influx_agg_1d"
        }

        table_name = allowed_tables.get(view)
        if not table_name:
            # Use default instead of error
            console.log(f"⚠️ Invalid aggregation view: {view}, using default 10m")
            return "influx_agg_10m"

        return table_name

    def _get_time_range_options(self, view: str) -> List[Dict[str, str]]:
        """집계 단위에 따른 시간 범위 옵션 반환"""
        if view == "1m":
            return [
                {"label": "최근 1시간", "value": "1 hour"},
                {"label": "최근 6시간", "value": "6 hours"},
                {"label": "최근 12시간", "value": "12 hours"},
                {"label": "최근 24시간", "value": "24 hours"},
                {"label": "최근 48시간", "value": "48 hours"},
            ]
        elif view == "10m":
            return [
                {"label": "최근 1일", "value": "24 hours"},
                {"label": "최근 3일", "value": "72 hours"},
                {"label": "최근 7일", "value": "168 hours"},
                {"label": "최근 14일", "value": "336 hours"},
                {"label": "최근 30일", "value": "720 hours"},
            ]
        elif view == "1h":
            return [
                {"label": "최근 7일", "value": "168 hours"},
                {"label": "최근 14일", "value": "336 hours"},
                {"label": "최근 30일", "value": "720 hours"},
                {"label": "최근 90일", "value": "2160 hours"},
                {"label": "최근 180일", "value": "4320 hours"},
            ]
        else:  # 1d
            return [
                {"label": "최근 30일", "value": "720 hours"},
                {"label": "최근 90일", "value": "2160 hours"},
                {"label": "최근 180일", "value": "4320 hours"},
                {"label": "최근 1년", "value": "8760 hours"},
                {"label": "최근 2년", "value": "17520 hours"},
            ]