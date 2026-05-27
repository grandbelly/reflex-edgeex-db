"""
실시간 알람 모니터링 엔진
타임스탬프 기반으로 센서 데이터를 감시하고 알람 이벤트를 생성
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import asyncpg
from ..db import get_pool

class AlarmMonitor:
    """실시간 알람 모니터링 엔진"""

    def __init__(self):
        self.pool = None
        self.rules = {}
        self.monitoring = False
        self.check_interval = 10  # 10초마다 체크

    async def initialize(self):
        """모니터 초기화"""
        self.pool = await get_pool()
        await self.load_alarm_rules()

    async def load_alarm_rules(self):
        """알람 규칙 로드"""
        async with self.pool.acquire() as conn:
            # QC rules를 알람 규칙으로 사용
            rows = await conn.fetch("""
                SELECT tag_name, min_val, max_val,
                       warn_min, warn_max,
                       alarm_min, alarm_max
                FROM influx_qc_rule
                WHERE active = true
            """)

            for row in rows:
                self.rules[row['tag_name']] = {
                    'normal': (row['min_val'], row['max_val']),
                    'warning': (row['warn_min'], row['warn_max']),
                    'critical': (row['alarm_min'], row['alarm_max'])
                }

    async def check_sensor_values(self):
        """센서 값 체크 및 알람 생성"""
        async with self.pool.acquire() as conn:
            # 최근 데이터 조회
            rows = await conn.fetch("""
                SELECT DISTINCT ON (tag_name)
                    tag_name, value, ts
                FROM influx_hist
                WHERE ts >= NOW() - INTERVAL '1 minute'
                ORDER BY tag_name, ts DESC
            """)

            for row in rows:
                await self.evaluate_alarm_condition(
                    conn,
                    row['tag_name'],
                    row['value'],
                    row['ts']
                )

    async def evaluate_alarm_condition(self, conn, tag_name: str, value: float, ts: datetime):
        """알람 조건 평가"""
        if tag_name not in self.rules:
            return

        rules = self.rules[tag_name]
        alarm_level = None
        message = None

        # Critical 체크
        if rules['critical']:
            alarm_min, alarm_max = rules['critical']
            if alarm_min and value < alarm_min:
                alarm_level = 4  # CRITICAL
                message = f"{tag_name} 값 {value:.2f}이(가) 위험 하한 {alarm_min}보다 낮습니다"
            elif alarm_max and value > alarm_max:
                alarm_level = 4  # CRITICAL
                message = f"{tag_name} 값 {value:.2f}이(가) 위험 상한 {alarm_max}를 초과했습니다"

        # Warning 체크
        if not alarm_level and rules['warning']:
            warn_min, warn_max = rules['warning']
            if warn_min and value < warn_min:
                alarm_level = 3  # WARNING
                message = f"{tag_name} 값 {value:.2f}이(가) 경고 하한 {warn_min}보다 낮습니다"
            elif warn_max and value > warn_max:
                alarm_level = 3  # WARNING
                message = f"{tag_name} 값 {value:.2f}이(가) 경고 상한 {warn_max}를 초과했습니다"

        # Normal 범위 벗어남 체크
        if not alarm_level and rules['normal']:
            min_val, max_val = rules['normal']
            if min_val and value < min_val:
                alarm_level = 2  # NOTICE
                message = f"{tag_name} 값 {value:.2f}이(가) 정상 하한 {min_val}보다 낮습니다"
            elif max_val and value > max_val:
                alarm_level = 2  # NOTICE
                message = f"{tag_name} 값 {value:.2f}이(가) 정상 상한 {max_val}를 초과했습니다"

        # 알람 생성
        if alarm_level:
            await self.create_alarm_event(conn, tag_name, value, ts, alarm_level, message)

    async def create_alarm_event(self, conn, tag_name: str, value: float,
                                 ts: datetime, level: int, message: str):
        """알람 이벤트 생성 및 저장"""

        # 중복 체크 (같은 태그, 레벨로 최근 5분내 알람이 있는지)
        existing = await conn.fetchval("""
            SELECT COUNT(*) FROM alarm_history
            WHERE sensor_data->>'tag_name' = $1
            AND level = $2
            AND triggered_at > NOW() - INTERVAL '5 minutes'
        """, tag_name, level)

        if existing > 0:
            return  # 중복 알람 방지

        # 알람 이벤트 생성
        event_id = f"ALM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{tag_name}"
        scenario_id = self._get_scenario_id(tag_name, level)

        sensor_data = {
            "tag_name": tag_name,
            "value": value,
            "timestamp": ts.isoformat()
        }

        # alarm_history에 저장
        await conn.execute("""
            INSERT INTO alarm_history
            (event_id, scenario_id, level, triggered_at, message, sensor_data, actions_taken)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, event_id, scenario_id, level, ts, message,
            json.dumps(sensor_data), ["알람 생성", "모니터링"])

        # NOTIFY 이벤트 발생 — use pg_notify() function for proper parameterization.
        # The previous `f"NOTIFY alarm_event, '{event_id}'"` pattern was a SQL
        # injection vector because event_id ultimately derives from sensor data
        # which can come from upstream untrusted sources.
        await conn.execute("SELECT pg_notify('alarm_event', $1)", event_id)

        print(f"✅ 알람 생성: {event_id} - {message}")

    def _get_scenario_id(self, tag_name: str, level: int) -> str:
        """시나리오 ID 생성"""
        tag_prefix = tag_name[:4] if len(tag_name) >= 4 else tag_name
        level_names = {1: "INFO", 2: "NOTICE", 3: "WARN", 4: "CRIT", 5: "EMRG"}
        return f"{tag_prefix}_{level_names.get(level, 'UNKN')}"

    async def start_monitoring(self):
        """모니터링 시작"""
        self.monitoring = True
        print("🚀 알람 모니터링 시작")

        while self.monitoring:
            try:
                await self.check_sensor_values()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ 모니터링 에러: {e}")
                await asyncio.sleep(5)

    async def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring = False
        print("🛑 알람 모니터링 중지")

# 싱글톤 인스턴스
alarm_monitor = AlarmMonitor()

async def start_alarm_monitoring():
    """알람 모니터링 시작"""
    await alarm_monitor.initialize()
    await alarm_monitor.start_monitoring()