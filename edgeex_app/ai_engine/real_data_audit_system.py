"""
🔍 실제 데이터 기반 품질 평가 시스템
TimescaleDB 1분 간격 데이터를 정확히 분석하여 누락을 검증
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import numpy as np

from edgeex_app.db import q


@dataclass
class DataGapAnalysis:
    """데이터 누락 분석 결과"""
    sensor_name: str
    analysis_period: str
    start_time: datetime
    end_time: datetime
    
    # 완벽한 1분 간격 시간 시퀀스
    expected_timestamps: List[datetime] = field(default_factory=list)
    actual_timestamps: List[datetime] = field(default_factory=list)
    missing_timestamps: List[datetime] = field(default_factory=list)
    
    # 기대 vs 실제 데이터 포인트
    expected_data_points: int = 0
    actual_data_points: int = 0
    missing_data_points: int = 0
    completeness_ratio: float = 0.0  # 완정성 비율 (0-1)
    
    # 시간대별 누락 히트맵 데이터
    hourly_completeness: Dict[int, float] = field(default_factory=dict)  # 시간별 완성도 (0-1)
    daily_completeness: Dict[str, float] = field(default_factory=dict)   # 일별 완성도 (0-1)
    
    # 연속 누락 구간
    gap_periods: List[Dict] = field(default_factory=list)
    
    # 품질 등급
    quality_grade: str = "UNKNOWN"
    quality_score: float = 0.0


class RealDataAuditSystem:
    """🔍 실제 데이터 기반 품질 감사 시스템"""
    
    def __init__(self):
        self.name = "RealDataAuditSystem"
        
        # 1분 간격 기준
        self.data_interval_minutes = 1
        self.minutes_per_hour = 60
        self.minutes_per_day = 1440
        
        # 품질 등급 기준
        self.quality_grades = {
            (0.98, 1.00): "EXCELLENT",  # 98-100%
            (0.95, 0.98): "GOOD",       # 95-98%
            (0.90, 0.95): "AVERAGE",    # 90-95%
            (0.80, 0.90): "POOR",       # 80-90%
            (0.00, 0.80): "CRITICAL"    # 0-80%
        }
    
    def generate_expected_timestamps(self, start_time: datetime, end_time: datetime) -> List[datetime]:
        """1분 간격으로 완벽한 타임스탬프 시퀀스 생성"""
        expected_timestamps = []
        
        # 시작 시간을 1분 단위로 정규화 (초, 마이크로초 제거)
        normalized_start = start_time.replace(second=0, microsecond=0)
        
        current_time = normalized_start
        while current_time <= end_time:
            expected_timestamps.append(current_time)
            current_time += timedelta(minutes=1)
        
        return expected_timestamps
    
    async def analyze_sensor_data_gaps(
        self, 
        sensor_name: str, 
        analysis_hours: int = 24
    ) -> DataGapAnalysis:
        """센서 데이터 누락 정밀 분석"""
        
        print(f"🔍 {sensor_name} 센서 데이터 누락 분석 시작 ({analysis_hours}시간)")
        
        # 분석 기간 설정
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time = end_time - timedelta(hours=analysis_hours)
        
        gap_analysis = DataGapAnalysis(
            sensor_name=sensor_name,
            analysis_period=f"{analysis_hours}시간",
            start_time=start_time,
            end_time=end_time
        )
        
        # 1. 완벽한 1분 간격 타임스탬프 생성
        gap_analysis.expected_timestamps = self.generate_expected_timestamps(start_time, end_time)
        gap_analysis.expected_data_points = len(gap_analysis.expected_timestamps)
        
        print(f"   📅 기대 데이터 포인트: {gap_analysis.expected_data_points}개 (1분 간격)")
        
        # 2. 실제 데이터 타임스탬프 조회
        actual_timestamps = await self._get_actual_timestamps(sensor_name, start_time, end_time)
        gap_analysis.actual_timestamps = actual_timestamps
        gap_analysis.actual_data_points = len(actual_timestamps)
        
        print(f"   📊 실제 데이터 포인트: {gap_analysis.actual_data_points}개")
        
        # 3. 누락된 타임스탬프 찾기
        actual_timestamp_set = set(actual_timestamps)
        gap_analysis.missing_timestamps = [
            ts for ts in gap_analysis.expected_timestamps 
            if ts not in actual_timestamp_set
        ]
        gap_analysis.missing_data_points = len(gap_analysis.missing_timestamps)
        gap_analysis.completeness_ratio = gap_analysis.actual_data_points / gap_analysis.expected_data_points
        
        print(f"   ❌ 누락 데이터 포인트: {gap_analysis.missing_data_points}개 ({(1-gap_analysis.completeness_ratio)*100:.1f}% 누락)")
        
        # 4. 시간대별 완성도 계산 (히트맵 데이터)
        gap_analysis.hourly_completeness = self._calculate_hourly_completeness(gap_analysis)
        
        # 5. 일별 완성도 계산 (다일 분석시)
        if analysis_hours >= 24:
            gap_analysis.daily_completeness = self._calculate_daily_completeness(gap_analysis)
        
        # 6. 연속 누락 구간 찾기
        gap_analysis.gap_periods = self._find_continuous_gap_periods(gap_analysis.missing_timestamps)
        
        # 7. 품질 등급 및 점수 계산
        gap_analysis.quality_grade = self._assign_quality_grade(gap_analysis.completeness_ratio)
        gap_analysis.quality_score = gap_analysis.completeness_ratio
        
        print(f"   🎯 데이터 완성도: {gap_analysis.completeness_ratio:.4f} ({gap_analysis.quality_grade})")
        
        return gap_analysis
    
    async def _get_actual_timestamps(
        self, 
        sensor_name: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[datetime]:
        """실제 데이터베이스에서 타임스탬프 조회"""
        
        try:
            # 1분 단위로 정규화된 타임스탬프만 조회
            query = """
            SELECT DISTINCT DATE_TRUNC('minute', ts) as normalized_ts
            FROM public.influx_hist 
            WHERE tag_name = %s 
            AND ts >= %s 
            AND ts <= %s
            ORDER BY normalized_ts
            """
            
            result = await q(query, (sensor_name, start_time, end_time))
            
            actual_timestamps = []
            for row in result:
                ts = row['normalized_ts']
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                
                # timezone 정보 제거 (비교를 위해)
                if ts.tzinfo:
                    ts = ts.replace(tzinfo=None)
                    
                actual_timestamps.append(ts)
            
            return actual_timestamps
            
        except Exception as e:
            print(f"   ❌ {sensor_name} 타임스탬프 조회 오류: {e}")
            return []
    
    def _calculate_hourly_completeness(self, gap_analysis: DataGapAnalysis) -> Dict[int, float]:
        """시간대별 완성도 계산 (24시간 히트맵용)"""
        
        hourly_completeness = {}
        
        # 각 시간대(0-23)별로 계산
        for hour in range(24):
            # 해당 시간대의 기대 타임스탬프들
            expected_in_hour = [
                ts for ts in gap_analysis.expected_timestamps 
                if ts.hour == hour
            ]
            
            # 해당 시간대의 실제 타임스탬프들
            actual_in_hour = [
                ts for ts in gap_analysis.actual_timestamps 
                if ts.hour == hour
            ]
            
            # 완성도 계산
            if len(expected_in_hour) > 0:
                completeness = len(actual_in_hour) / len(expected_in_hour)
            else:
                completeness = 1.0  # 해당 시간대에 데이터가 없어야 정상인 경우
                
            hourly_completeness[hour] = completeness
        
        return hourly_completeness
    
    def _calculate_daily_completeness(self, gap_analysis: DataGapAnalysis) -> Dict[str, float]:
        """일별 완성도 계산 (다일 히트맵용)"""
        
        daily_completeness = {}
        
        # 분석 기간의 모든 날짜
        current_date = gap_analysis.start_time.date()
        end_date = gap_analysis.end_time.date()
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 해당 날짜의 기대 타임스탬프들
            expected_in_day = [
                ts for ts in gap_analysis.expected_timestamps 
                if ts.date() == current_date
            ]
            
            # 해당 날짜의 실제 타임스탬프들
            actual_in_day = [
                ts for ts in gap_analysis.actual_timestamps 
                if ts.date() == current_date
            ]
            
            # 완성도 계산
            if len(expected_in_day) > 0:
                completeness = len(actual_in_day) / len(expected_in_day)
            else:
                completeness = 1.0
                
            daily_completeness[date_str] = completeness
            current_date += timedelta(days=1)
        
        return daily_completeness
    
    def _find_continuous_gap_periods(self, missing_timestamps: List[datetime]) -> List[Dict]:
        """연속된 누락 구간 찾기"""
        
        if not missing_timestamps:
            return []
        
        # 타임스탬프 정렬
        sorted_missing = sorted(missing_timestamps)
        
        gap_periods = []
        current_start = sorted_missing[0]
        current_end = sorted_missing[0]
        
        for i in range(1, len(sorted_missing)):
            current_ts = sorted_missing[i]
            expected_next = current_end + timedelta(minutes=1)
            
            if current_ts == expected_next:
                # 연속된 누락
                current_end = current_ts
            else:
                # 누락 구간 끝남
                duration_minutes = int((current_end - current_start).total_seconds() / 60) + 1
                gap_periods.append({
                    "start": current_start,
                    "end": current_end,
                    "duration_minutes": duration_minutes,
                    "severity": "critical" if duration_minutes > 60 else "warning" if duration_minutes > 10 else "minor"
                })
                
                # 새로운 구간 시작
                current_start = current_ts
                current_end = current_ts
        
        # 마지막 구간 추가
        duration_minutes = int((current_end - current_start).total_seconds() / 60) + 1
        gap_periods.append({
            "start": current_start,
            "end": current_end,
            "duration_minutes": duration_minutes,
            "severity": "critical" if duration_minutes > 60 else "warning" if duration_minutes > 10 else "minor"
        })
        
        # 심각도순으로 정렬하고 상위 10개만 반환
        severity_order = {"critical": 3, "warning": 2, "minor": 1}
        gap_periods.sort(key=lambda x: (severity_order[x["severity"]], x["duration_minutes"]), reverse=True)
        
        return gap_periods[:10]
    
    def _assign_quality_grade(self, completeness_ratio: float) -> str:
        """완성도 비율에 따른 품질 등급 부여"""
        
        for (min_ratio, max_ratio), grade in self.quality_grades.items():
            if min_ratio <= completeness_ratio <= max_ratio:
                return grade
        
        return "UNKNOWN"
    
    async def generate_multi_sensor_heatmap(
        self, 
        sensor_names: List[str], 
        analysis_hours: int = 24
    ) -> Dict:
        """여러 센서의 데이터 누락 히트맵 생성"""
        
        print(f"🗺️ {len(sensor_names)}개 센서 데이터 누락 히트맵 생성 ({analysis_hours}시간)")
        
        heatmap_data = {
            "sensors": sensor_names,
            "analysis_hours": analysis_hours,
            "hourly_heatmap": [],  # 시간별 히트맵 데이터
            "daily_heatmap": [],   # 일별 히트맵 데이터 (24시간 이상 분석시)
            "summary": {},
            "gap_details": {}
        }
        
        total_completeness = 0.0
        sensor_analyses = {}
        
        # 각 센서별 분석 수행
        for sensor_name in sensor_names:
            print(f"\n📊 {sensor_name} 분석 중...")
            
            gap_analysis = await self.analyze_sensor_data_gaps(sensor_name, analysis_hours)
            sensor_analyses[sensor_name] = gap_analysis
            total_completeness += gap_analysis.completeness_ratio
            
            # 시간별 히트맵 데이터 추가
            for hour, completeness in gap_analysis.hourly_completeness.items():
                heatmap_data["hourly_heatmap"].append({
                    "sensor": sensor_name,
                    "hour": hour,
                    "completeness": completeness,
                    "missing_count": int((1 - completeness) * (analysis_hours // 24 if analysis_hours >= 24 else 1) * 60),
                    "status": "excellent" if completeness >= 0.98 else 
                             "good" if completeness >= 0.95 else 
                             "average" if completeness >= 0.90 else 
                             "poor" if completeness >= 0.80 else "critical"
                })
            
            # 일별 히트맵 데이터 추가 (24시간 이상 분석시)
            if analysis_hours >= 24:
                for date_str, completeness in gap_analysis.daily_completeness.items():
                    heatmap_data["daily_heatmap"].append({
                        "sensor": sensor_name,
                        "date": date_str,
                        "completeness": completeness,
                        "missing_count": int((1 - completeness) * 1440),  # 하루 1440분
                        "status": "excellent" if completeness >= 0.98 else 
                                 "good" if completeness >= 0.95 else 
                                 "average" if completeness >= 0.90 else 
                                 "poor" if completeness >= 0.80 else "critical"
                    })
            
            # 누락 상세 정보
            heatmap_data["gap_details"][sensor_name] = {
                "total_missing": gap_analysis.missing_data_points,
                "completeness_ratio": gap_analysis.completeness_ratio,
                "quality_grade": gap_analysis.quality_grade,
                "major_gaps": [
                    {
                        "start": gap["start"].strftime("%Y-%m-%d %H:%M"),
                        "end": gap["end"].strftime("%Y-%m-%d %H:%M"),
                        "duration_minutes": gap["duration_minutes"],
                        "severity": gap["severity"]
                    }
                    for gap in gap_analysis.gap_periods[:3]  # 상위 3개만
                ]
            }
        
        # 전체 요약 통계
        avg_completeness = total_completeness / len(sensor_names) if sensor_names else 0
        
        grade_counts = {}
        for analysis in sensor_analyses.values():
            grade = analysis.quality_grade
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        heatmap_data["summary"] = {
            "total_sensors": len(sensor_names),
            "average_completeness": avg_completeness,
            "overall_grade": self._assign_quality_grade(avg_completeness),
            "grade_distribution": grade_counts,
            "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_expected_points": sum(a.expected_data_points for a in sensor_analyses.values()),
            "total_missing_points": sum(a.missing_data_points for a in sensor_analyses.values())
        }
        
        print(f"\n🎯 히트맵 생성 완료:")
        print(f"   - 전체 평균 완성도: {avg_completeness:.4f}")
        print(f"   - 전체 등급: {heatmap_data['summary']['overall_grade']}")
        print(f"   - 총 누락 포인트: {heatmap_data['summary']['total_missing_points']:,}개")
        
        return heatmap_data


# 전역 실제 데이터 감사 시스템
real_audit_system = RealDataAuditSystem()


async def analyze_sensor_gaps(sensor_name: str, hours: int = 24) -> DataGapAnalysis:
    """센서 데이터 누락 분석"""
    return await real_audit_system.analyze_sensor_data_gaps(sensor_name, hours)


async def generate_sensors_heatmap(sensor_names: List[str], hours: int = 24) -> Dict:
    """센서들의 데이터 누락 히트맵 생성"""
    return await real_audit_system.generate_multi_sensor_heatmap(sensor_names, hours)