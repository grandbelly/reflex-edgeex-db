"""
📊 판다스 기반 동적 데이터 분석 엔진
히트맵, 상관성, 예측 분석까지 포함한 완전한 데이터 분석 시스템
"""

import asyncio
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import pearsonr, spearmanr
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import warnings
import io
import base64
import json
import logging

# 머신러닝 라이브러리
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import xgboost as xgb
import lightgbm as lgb
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose

from edgeex_app.db import q

warnings.filterwarnings('ignore')

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    analysis_type: str
    title: str
    description: str
    
    # 데이터
    dataframe: Optional[pd.DataFrame] = None
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    
    # 시각화
    chart_data: Dict[str, Any] = field(default_factory=dict)
    heatmap_data: Optional[Dict] = None
    
    # 분석 결과
    insights: List[str] = field(default_factory=list)
    correlations: Dict[str, float] = field(default_factory=dict)
    predictions: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict] = field(default_factory=list)
    
    # 메타데이터
    analysis_time: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0
    data_quality_score: float = 0.0


class PandasAnalysisEngine:
    """📊 판다스 기반 동적 데이터 분석 엔진"""
    
    def __init__(self):
        self.name = "PandasAnalysisEngine"
        
        # 분석 설정
        self.default_lookback_hours = 168  # 1주일
        self.min_data_points = 30          # 최소 데이터 포인트 (100 -> 30으로 완화)
        self.correlation_threshold = 0.3   # 상관성 임계값
        self.anomaly_threshold = 2.0       # 이상치 임계값 (표준편차)
        
        # 시각화 설정
        plt.style.use('default')
        sns.set_palette("husl")
    
    async def analyze_sensor_data(
        self,
        sensors: List[str],
        analysis_type: str,
        hours: int = 168,
        **kwargs
    ) -> AnalysisResult:
        """동적 센서 데이터 분석"""
        
        print(f"[ANALYSIS] {analysis_type} - sensors: {sensors}, hours: {hours}")
        
        # 1. 데이터 수집
        df = await self._collect_sensor_data(sensors, hours)
        
        if df.empty or len(df) < self.min_data_points:
            return AnalysisResult(
                analysis_type=analysis_type,
                title="데이터 부족",
                description=f"분석에 충분한 데이터가 없습니다. (최소 {self.min_data_points}개 필요)",
                insights=["데이터 수집 기간을 늘리거나 센서를 추가해주세요."]
            )
        
        print(f"[DONE] Data collected - {len(df)} rows x {len(df.columns)} columns")
        
        # 2. 분석 타입별 처리
        if analysis_type == "correlation":
            return await self._analyze_correlations(df, sensors, hours)
        elif analysis_type == "heatmap":
            return await self._analyze_heatmaps(df, sensors, hours)
        elif analysis_type == "prediction":
            return await self._analyze_predictions(df, sensors, hours, **kwargs)
        elif analysis_type == "anomaly":
            return await self._analyze_anomalies(df, sensors, hours)
        elif analysis_type == "comprehensive":
            return await self._comprehensive_analysis(df, sensors, hours)
        else:
            return await self._basic_statistical_analysis(df, sensors, hours)
    
    async def _collect_sensor_data(self, sensors: List[str], hours: int) -> pd.DataFrame:
        """센서 데이터 수집 및 DataFrame 변환 - 품질 개선"""
        
        logger.info(f"[INFO] Data collection start - sensors: {sensors}, hours: {hours}")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        logger.debug(f"시간 범위: {start_time} ~ {end_time}")
        
        # SQL 쿼리로 데이터 수집 - 품질 필터 추가
        sensor_placeholders = ','.join(['%s'] * len(sensors))
        query = f"""
        SELECT 
            ts,
            tag_name,
            value
        FROM public.influx_hist 
        WHERE tag_name IN ({sensor_placeholders})
        AND ts >= %s 
        AND ts <= %s
        AND value IS NOT NULL
        -- 센서별 유효 범위 적용 (D1xx: -50~500, D2xx: -100~5000, D3xx: -1000~30000)
        AND (
            (tag_name LIKE 'D1%%' AND value >= -50 AND value <= 500) OR
            (tag_name LIKE 'D2%%' AND value >= -100 AND value <= 5000) OR
            (tag_name LIKE 'D3%%' AND value >= -1000 AND value <= 30000) OR
            (tag_name NOT LIKE 'D%%' AND value > 0 AND value < 10000)
        )
        ORDER BY ts, tag_name
        """
        
        logger.debug(f"SQL 쿼리 파라미터: 센서={sensors}, 시작={start_time}, 종료={end_time}")
        
        try:
            result = await q(query, sensors + [start_time, end_time])
            
            if not result:
                logger.warning(f"쿼리 결과 없음 - 센서: {sensors}")
                return pd.DataFrame()
            
            logger.info(f"쿼리 결과: {len(result)}개 레코드 반환")
            
            # DataFrame 생성
            data = []
            sensor_value_ranges = {}  # 센서별 값 범위 추적
            
            for row in result:
                sensor_name = row['tag_name']
                value = float(row['value'])
                
                # 센서별 값 범위 추적
                if sensor_name not in sensor_value_ranges:
                    sensor_value_ranges[sensor_name] = {'min': value, 'max': value, 'count': 0}
                sensor_value_ranges[sensor_name]['min'] = min(sensor_value_ranges[sensor_name]['min'], value)
                sensor_value_ranges[sensor_name]['max'] = max(sensor_value_ranges[sensor_name]['max'], value)
                sensor_value_ranges[sensor_name]['count'] += 1
                
                data.append({
                    'timestamp': row['ts'],
                    'sensor': sensor_name,
                    'value': value
                })
            
            # 센서별 값 범위 로깅
            logger.info(f"[INFO] Sensor value ranges:")
            for sensor, ranges in sensor_value_ranges.items():
                logger.info(f"   - {sensor}: min={ranges['min']:.2f}, max={ranges['max']:.2f}, count={ranges['count']}")
            
            df = pd.DataFrame(data)
            
            # 타임스탬프 인덱스 설정
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            print(f"[INFO] Collected data info:")
            print(f"   - 총 레코드: {len(df)}개")
            print(f"   - 센서별 데이터: {df.groupby('sensor').size().to_dict()}")
            print(f"   - 시간 범위: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
            
            logger.info(f"DataFrame 생성 완료: {len(df)}개 레코드, {df['sensor'].nunique()}개 센서")
            
            # 피벗 테이블 생성 전에 데이터가 충분한지 확인
            sensor_counts = df.groupby('sensor').size()
            # 최소 데이터 포인트 요구사항 완화 (10 -> 3)
            MIN_DATA_POINTS = 3  # 상관분석에는 최소 3개면 충분
            sufficient_sensors = sensor_counts[sensor_counts >= MIN_DATA_POINTS].index.tolist()
            
            print(f"[INFO] Sensor data points check:")
            for sensor, count in sensor_counts.items():
                status = "[OK]" if count >= MIN_DATA_POINTS else "[FAIL]"
                print(f"   {status} {sensor}: {count}개 (최소 {MIN_DATA_POINTS}개 필요)")
                logger.debug(f"센서 {sensor}: {count}개 데이터 포인트 {'(충분)' if count >= MIN_DATA_POINTS else '(부족)'}")
            
            if not sufficient_sensors:
                print("[ERROR] Not enough data for analysis")
                logger.error(f"모든 센서가 최소 데이터 포인트 요구사항({MIN_DATA_POINTS}개)을 만족하지 못함")
                return pd.DataFrame()
            
            # 충분한 데이터가 있는 센서만 사용
            df_filtered = df[df['sensor'].isin(sufficient_sensors)]
            logger.info(f"필터링 후: {len(df_filtered)}개 레코드, 센서: {sufficient_sensors}")
            
            # 피벗 테이블로 센서별 컬럼 생성
            pivot_df = df_filtered.pivot_table(
                index='timestamp', 
                columns='sensor', 
                values='value',
                aggfunc='mean'  # 같은 시간에 여러 값이 있으면 평균
            )
            
            print(f"[INFO] After pivot:")
            print(f"   - Shape: {pivot_df.shape}")
            print(f"   - 센서: {list(pivot_df.columns)}")
            print(f"   - 결측치 비율: {pivot_df.isnull().sum().sum() / (pivot_df.shape[0] * pivot_df.shape[1]):.3f}")
            
            logger.info(f"피벗 테이블 생성: shape={pivot_df.shape}, 컬럼={list(pivot_df.columns)}")
            
            # 결측치가 너무 많으면 보간 스킵
            missing_ratio = pivot_df.isnull().sum().sum() / (pivot_df.shape[0] * pivot_df.shape[1])
            if missing_ratio > 0.5:
                print("[WARNING] Missing values > 50%, skipping interpolation")
                logger.warning(f"높은 결측치 비율 ({missing_ratio:.1%}), 보간 스킵")
            else:
                # 필요한 경우에만 간단한 보간
                pivot_df = pivot_df.fillna(method='ffill').fillna(method='bfill')
                logger.debug("결측치 보간 완료 (forward fill + backward fill)")
            
            # 시간 관련 특성 추가
            result_df = pivot_df.reset_index()
            result_df['hour'] = result_df['timestamp'].dt.hour
            result_df['day_of_week'] = result_df['timestamp'].dt.dayofweek
            result_df['is_weekend'] = result_df['day_of_week'].isin([5, 6])
            
            logger.info(f"[SUCCESS] Final DataFrame: shape={result_df.shape}, sensors={[c for c in result_df.columns if c not in ['timestamp', 'hour', 'day_of_week', 'is_weekend']]}")
            
            return result_df
            
        except Exception as e:
            print(f"[ERROR] Data collection error: {e}")
            logger.error(f"데이터 수집 중 오류 발생: {e}", exc_info=True)
            return pd.DataFrame()
    
    async def _analyze_correlations(self, df: pd.DataFrame, sensors: List[str], hours: int) -> AnalysisResult:
        """센서 간 상관성 분석"""
        
        print(f"[START] Correlation analysis:")
        print(f"   - Requested sensors: {sensors}")
        print(f"   - DataFrame columns: {list(df.columns)}")
        
        # DataFrame에 실제 존재하는 센서만 추출
        available_sensors = [s for s in sensors if s in df.columns]
        print(f"   - Available sensors: {available_sensors}")
        
        if len(available_sensors) < 2:
            print("[ERROR] Not enough sensors for correlation analysis (need at least 2)")
            return AnalysisResult(
                analysis_type="correlation",
                title="상관관계 분석 실패",
                description="분석에 필요한 센서 데이터가 부족합니다",
                dataframe=df,
                insights=["센서 데이터가 부족하여 상관관계를 분석할 수 없습니다"],
                confidence_score=0.0,
                data_quality_score=0.0
            )
        
        # 센서 데이터만 추출
        sensor_data = df[available_sensors].select_dtypes(include=[np.number])
        
        # NaN 값 처리 - 데이터 품질 확인
        print(f"[INFO] Data quality check:")
        for sensor in available_sensors:
            null_count = sensor_data[sensor].isnull().sum()
            total_count = len(sensor_data[sensor])
            null_pct = (null_count / total_count) * 100 if total_count > 0 else 100
            print(f"   - {sensor}: {null_count}/{total_count} NaN ({null_pct:.1f}%)")
        
        # NaN 값이 있는 행 제거 (상관계수 계산을 위해)
        sensor_data_clean = sensor_data.dropna()
        print(f"[INFO] After cleaning: {len(sensor_data)} -> {len(sensor_data_clean)} rows")
        
        if len(sensor_data_clean) < 5:
            print("[ERROR] Not enough valid data for correlation analysis (need at least 5 rows)")
            return AnalysisResult(
                analysis_type="correlation",
                title="상관관계 분석 실패",
                description="NaN 제거 후 유효 데이터가 부족합니다",
                dataframe=df,
                insights=["유효한 데이터가 부족하여 상관관계를 분석할 수 없습니다", f"전체 {len(sensor_data)}행 중 유효 {len(sensor_data_clean)}행"],
                confidence_score=0.0,
                data_quality_score=len(sensor_data_clean) / len(sensor_data) if len(sensor_data) > 0 else 0.0
            )
        
        # 피어슨 상관계수 (NaN이 없는 정제된 데이터로 계산)
        pearson_corr = sensor_data_clean.corr(method='pearson')
        
        # 스피어만 상관계수
        spearman_corr = sensor_data_clean.corr(method='spearman')
        
        # NaN 값 확인
        pearson_nan_count = pearson_corr.isnull().sum().sum()
        if pearson_nan_count > 0:
            print(f"[WARNING] NaN found in correlation matrix: {pearson_nan_count}")
            # NaN을 0으로 채우기 (대각선 외)
            pearson_corr = pearson_corr.fillna(0)
            spearman_corr = spearman_corr.fillna(0)
        
        print(f"[SUCCESS] Final correlation matrix shape: {pearson_corr.shape}")
        print(f"   - NaN 개수: {pearson_corr.isnull().sum().sum()}")
        
        # 상관성 히트맵 데이터
        heatmap_data = {
            'pearson': pearson_corr.round(3).to_dict(),
            'spearman': spearman_corr.round(3).to_dict(),
            'sensors': available_sensors
        }
        
        print(f"[SUCCESS] Correlation heatmap data created:")
        print(f"   - Pearson 상관계수 크기: {pearson_corr.shape}")
        print(f"   - 센서: {available_sensors}")
        print(f"   - 샘플 상관계수: {pearson_corr.iloc[0, 1] if pearson_corr.shape[0] > 1 else 'N/A'}")
        
        # 높은 상관성 쌍 찾기 (available_sensors 기준으로 수정)
        correlations = {}
        strong_correlations = []
        
        for i in range(len(available_sensors)):
            for j in range(i+1, len(available_sensors)):
                sensor1, sensor2 = available_sensors[i], available_sensors[j]
                if sensor1 in pearson_corr.index and sensor2 in pearson_corr.columns:
                    corr_val = pearson_corr.loc[sensor1, sensor2]
                    # NaN 체크 및 처리
                    if pd.isna(corr_val):
                        print(f"[WARNING] {sensor1}-{sensor2} correlation is NaN")
                        corr_val = 0.0
                    
                    correlations[f"{sensor1}-{sensor2}"] = corr_val
                    
                    if abs(corr_val) > self.correlation_threshold:
                        strong_correlations.append({
                            'sensor1': sensor1,
                            'sensor2': sensor2,
                            'correlation': corr_val,
                            'strength': 'strong' if abs(corr_val) > 0.7 else 'moderate'
                        })
        
        # 인사이트 생성
        insights = []
        if strong_correlations:
            insights.append(f"총 {len(strong_correlations)}개의 유의미한 상관관계 발견")
            
            # 가장 높은 상관관계
            highest = max(strong_correlations, key=lambda x: abs(x['correlation']))
            insights.append(f"가장 높은 상관관계: {highest['sensor1']} ↔ {highest['sensor2']} ({highest['correlation']:.3f})")
            
            # 양의 상관관계
            positive_corrs = [c for c in strong_correlations if c['correlation'] > 0]
            if positive_corrs:
                insights.append(f"양의 상관관계: {len(positive_corrs)}개 (동시 증감 경향)")
            
            # 음의 상관관계  
            negative_corrs = [c for c in strong_correlations if c['correlation'] < 0]
            if negative_corrs:
                insights.append(f"음의 상관관계: {len(negative_corrs)}개 (반대 변화 경향)")
        else:
            insights.append("센서 간 유의미한 상관관계가 발견되지 않음")
            insights.append("각 센서가 독립적으로 동작하는 것으로 추정")
        
        # 데이터 품질 점수 계산
        data_quality = len(sensor_data_clean) / len(sensor_data) if len(sensor_data) > 0 else 0.0
        confidence = min(1.0, len(sensor_data_clean) / 100) * (1 - pearson_nan_count / (len(available_sensors) ** 2))
        
        return AnalysisResult(
            analysis_type="correlation",
            title=f"센서 상관성 분석 ({hours}시간)",
            description=f"{len(available_sensors)}개 센서 간 상관관계 분석 (유효 데이터 {len(sensor_data_clean)}행)",
            dataframe=df,
            heatmap_data=heatmap_data,
            correlations=correlations,
            insights=insights,
            confidence_score=confidence,
            data_quality_score=data_quality
        )
    
    async def _analyze_heatmaps(self, df: pd.DataFrame, sensors: List[str], hours: int) -> AnalysisResult:
        """다차원 히트맵 분석 (시간 패턴, 센서 관계 등)"""
        
        # 1. 시간대별 히트맵 (24시간 x 센서)
        df['hour'] = df['timestamp'].dt.hour
        hourly_heatmap = df.groupby('hour')[sensors].mean()
        
        # 2. 요일별 히트맵 (7일 x 센서)  
        df['day_of_week'] = df['timestamp'].dt.day_name()
        daily_heatmap = df.groupby('day_of_week')[sensors].mean()
        
        # 3. 센서 간 상관성 히트맵
        correlation_heatmap = df[sensors].corr()
        
        # 4. 이상치 히트맵 (Z-score 기반)
        z_scores = np.abs(stats.zscore(df[sensors]))
        anomaly_heatmap = (z_scores > 2).astype(int)  # 이상치를 1로 표시
        
        # 히트맵 데이터 구성
        heatmap_data = {
            'hourly': {
                'data': hourly_heatmap.round(2).to_dict(),
                'index': list(range(24)),
                'columns': sensors,
                'title': '시간대별 센서 평균값'
            },
            'daily': {
                'data': daily_heatmap.round(2).to_dict(),
                'index': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                'columns': sensors,
                'title': '요일별 센서 평균값'
            },
            'correlation': {
                'data': correlation_heatmap.round(3).to_dict(),
                'index': sensors,
                'columns': sensors,
                'title': '센서 간 상관성'
            },
            'anomaly': {
                'data': {sensor: int(anomaly_heatmap[sensor].sum()) for sensor in sensors},
                'index': ['이상치 개수'],
                'columns': sensors,
                'title': '센서별 이상치 발생 빈도'
            }
        }
        
        # 시간 패턴 인사이트
        insights = []
        
        # 시간대별 패턴 분석
        peak_hours = {}
        for sensor in sensors:
            if sensor in hourly_heatmap.columns:
                peak_hour = hourly_heatmap[sensor].idxmax()
                min_hour = hourly_heatmap[sensor].idxmin()
                peak_hours[sensor] = {'peak': peak_hour, 'min': min_hour}
                insights.append(f"{sensor}: {peak_hour}시 최대, {min_hour}시 최소")
        
        # 요일별 패턴 분석
        weekend_avg = daily_heatmap.loc[['Saturday', 'Sunday'], sensors].mean()
        weekday_avg = daily_heatmap.loc[['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], sensors].mean()
        
        for sensor in sensors:
            if sensor in weekend_avg.index:
                weekend_val = weekend_avg[sensor]
                weekday_val = weekday_avg[sensor]
                ratio = weekend_val / weekday_val if weekday_val != 0 else 1
                
                if ratio > 1.1:
                    insights.append(f"{sensor}: 주말이 평일보다 {(ratio-1)*100:.1f}% 높음")
                elif ratio < 0.9:
                    insights.append(f"{sensor}: 주말이 평일보다 {(1-ratio)*100:.1f}% 낮음")
        
        return AnalysisResult(
            analysis_type="heatmap",
            title=f"다차원 히트맵 분석 ({hours}시간)",
            description="시간별, 요일별, 상관성, 이상치 히트맵 종합 분석",
            dataframe=df,
            heatmap_data=heatmap_data,
            insights=insights,
            confidence_score=0.85,
            data_quality_score=min(1.0, len(df) / (hours * 60))
        )
    
    async def _analyze_predictions(self, df: pd.DataFrame, sensors: List[str], hours: int, **kwargs) -> AnalysisResult:
        """머신러닝 기반 예측 분석"""
        
        target_sensor = kwargs.get('target_sensor', sensors[0])
        prediction_horizon = kwargs.get('prediction_horizon', 24)  # 24시간 예측
        
        if target_sensor not in df.columns:
            return AnalysisResult(
                analysis_type="prediction",
                title="예측 실패",
                description=f"타겟 센서 {target_sensor}를 찾을 수 없습니다",
                insights=["유효한 센서 이름을 지정해주세요"]
            )
        
        # 특성 엔지니어링
        feature_df = df.copy()
        
        # 시간 특성
        feature_df['hour_sin'] = np.sin(2 * np.pi * feature_df['hour'] / 24)
        feature_df['hour_cos'] = np.cos(2 * np.pi * feature_df['hour'] / 24)
        feature_df['day_sin'] = np.sin(2 * np.pi * feature_df['day_of_week'] / 7)
        feature_df['day_cos'] = np.cos(2 * np.pi * feature_df['day_of_week'] / 7)
        
        # 지연 특성 (lag features)
        for lag in [1, 3, 6, 12, 24]:
            feature_df[f'{target_sensor}_lag_{lag}'] = feature_df[target_sensor].shift(lag)
        
        # 이동평균 특성
        for window in [3, 6, 12, 24]:
            feature_df[f'{target_sensor}_ma_{window}'] = feature_df[target_sensor].rolling(window=window).mean()
        
        # 결측치 제거
        feature_df = feature_df.dropna()
        
        if len(feature_df) < 100:
            return AnalysisResult(
                analysis_type="prediction",
                title="데이터 부족",
                description="예측 모델 학습에 필요한 데이터가 부족합니다",
                insights=["더 긴 기간의 데이터가 필요합니다"]
            )
        
        # 특성과 타겟 분리
        feature_columns = [col for col in feature_df.columns if col not in ['timestamp', target_sensor]]
        X = feature_df[feature_columns]
        y = feature_df[target_sensor]
        
        # 학습/검증 분할
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        # 여러 모델로 예측
        models = {}
        predictions = {}
        
        # 1. Random Forest
        try:
            rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            rf_model.fit(X_train, y_train)
            rf_pred = rf_model.predict(X_test)
            rf_score = r2_score(y_test, rf_pred)
            models['RandomForest'] = {'model': rf_model, 'score': rf_score, 'predictions': rf_pred}
        except Exception as e:
            print(f"RandomForest 모델 오류: {e}")
        
        # 2. XGBoost
        try:
            xgb_model = xgb.XGBRegressor(n_estimators=100, random_state=42)
            xgb_model.fit(X_train, y_train)
            xgb_pred = xgb_model.predict(X_test)
            xgb_score = r2_score(y_test, xgb_pred)
            models['XGBoost'] = {'model': xgb_model, 'score': xgb_score, 'predictions': xgb_pred}
        except Exception as e:
            print(f"XGBoost 모델 오류: {e}")
        
        # 3. Linear Regression
        try:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            lr_model = LinearRegression()
            lr_model.fit(X_train_scaled, y_train)
            lr_pred = lr_model.predict(X_test_scaled)
            lr_score = r2_score(y_test, lr_pred)
            models['LinearRegression'] = {'model': lr_model, 'score': lr_score, 'predictions': lr_pred, 'scaler': scaler}
        except Exception as e:
            print(f"LinearRegression 모델 오류: {e}")
        
        # 최적 모델 선택
        if not models:
            return AnalysisResult(
                analysis_type="prediction",
                title="모델 학습 실패",
                description="모든 예측 모델 학습에 실패했습니다",
                insights=["데이터 품질을 확인해주세요"]
            )
        
        best_model_name = max(models.keys(), key=lambda k: models[k]['score'])
        best_model = models[best_model_name]
        
        # 미래 예측 생성
        last_timestamp = df['timestamp'].max()
        future_timestamps = pd.date_range(
            start=last_timestamp + timedelta(hours=1),
            periods=prediction_horizon,
            freq='H'
        )
        
        # 미래 예측을 위한 특성 생성 (단순화)
        future_predictions = []
        last_known_value = y.iloc[-1]
        
        for i in range(prediction_horizon):
            # 단순 트렌드 기반 예측 (실제로는 더 복잡한 로직 필요)
            trend = np.mean(np.diff(y.tail(24)))  # 최근 24시간 트렌드
            predicted_value = last_known_value + trend * (i + 1)
            future_predictions.append(predicted_value)
        
        # 예측 결과 구성
        predictions = {
            'model_name': best_model_name,
            'model_score': best_model['score'],
            'test_mae': mean_absolute_error(y_test, best_model['predictions']),
            'test_rmse': np.sqrt(mean_squared_error(y_test, best_model['predictions'])),
            'future_predictions': [
                {
                    'timestamp': ts.isoformat(),
                    'predicted_value': pred,
                    'confidence': max(0.5, best_model['score'])  # 모델 스코어 기반 신뢰도
                }
                for ts, pred in zip(future_timestamps, future_predictions)
            ]
        }
        
        # 인사이트 생성
        insights = []
        insights.append(f"최적 모델: {best_model_name} (R² = {best_model['score']:.3f})")
        insights.append(f"예측 오차: MAE = {predictions['test_mae']:.2f}")
        
        if best_model['score'] > 0.8:
            insights.append("높은 예측 정확도 - 신뢰할 만한 예측")
        elif best_model['score'] > 0.6:
            insights.append("보통 예측 정확도 - 참고용으로 활용")
        else:
            insights.append("낮은 예측 정확도 - 추가 특성 필요")
        
        # 트렌드 분석
        trend = np.mean(future_predictions) - last_known_value
        if abs(trend) > 0.1:
            direction = "상승" if trend > 0 else "하락"
            insights.append(f"{prediction_horizon}시간 후 {direction} 트렌드 예측")
        
        return AnalysisResult(
            analysis_type="prediction",
            title=f"{target_sensor} 예측 분석 ({prediction_horizon}시간)",
            description=f"{best_model_name} 모델 기반 {target_sensor} 센서 예측",
            dataframe=feature_df,
            predictions=predictions,
            insights=insights,
            confidence_score=best_model['score'],
            data_quality_score=min(1.0, len(df) / (hours * 60))
        )
    
    async def _analyze_anomalies(self, df: pd.DataFrame, sensors: List[str], hours: int) -> AnalysisResult:
        """이상치 탐지 분석"""
        
        anomalies = []
        sensor_data = df[sensors].select_dtypes(include=[np.number])
        
        # 1. 통계적 이상치 탐지 (Z-score)
        z_scores = np.abs(stats.zscore(sensor_data))
        statistical_anomalies = []
        
        for sensor in sensors:
            if sensor in z_scores.columns:
                anomaly_mask = z_scores[sensor] > self.anomaly_threshold
                anomaly_indices = df[anomaly_mask].index.tolist()
                
                for idx in anomaly_indices:
                    statistical_anomalies.append({
                        'sensor': sensor,
                        'timestamp': df.loc[idx, 'timestamp'],
                        'value': df.loc[idx, sensor],
                        'z_score': z_scores.loc[idx, sensor],
                        'type': 'statistical',
                        'severity': 'high' if z_scores.loc[idx, sensor] > 3 else 'medium'
                    })
        
        # 2. 머신러닝 기반 이상치 탐지 (Isolation Forest)
        ml_anomalies = []
        try:
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            anomaly_labels = iso_forest.fit_predict(sensor_data)
            anomaly_scores = iso_forest.score_samples(sensor_data)
            
            anomaly_mask = anomaly_labels == -1
            anomaly_indices = df[anomaly_mask].index.tolist()
            
            for idx in anomaly_indices:
                # 가장 이상한 센서 찾기
                sensor_values = {sensor: abs(z_scores.loc[idx, sensor]) for sensor in sensors if sensor in z_scores.columns}
                most_anomalous_sensor = max(sensor_values.keys(), key=sensor_values.get) if sensor_values else sensors[0]
                
                ml_anomalies.append({
                    'sensor': most_anomalous_sensor,
                    'timestamp': df.loc[idx, 'timestamp'],
                    'value': df.loc[idx, most_anomalous_sensor],
                    'anomaly_score': anomaly_scores[idx],
                    'type': 'ml_isolation',
                    'severity': 'high' if anomaly_scores[idx] < -0.5 else 'medium'
                })
        except Exception as e:
            print(f"Isolation Forest 오류: {e}")
        
        # 모든 이상치 합치기
        all_anomalies = statistical_anomalies + ml_anomalies
        
        # 시간순 정렬 및 상위 20개만 선택
        all_anomalies.sort(key=lambda x: x['timestamp'], reverse=True)
        top_anomalies = all_anomalies[:20]
        
        # 인사이트 생성
        insights = []
        insights.append(f"총 {len(all_anomalies)}개의 이상치 탐지")
        
        if top_anomalies:
            # 센서별 이상치 개수
            sensor_anomaly_counts = {}
            for anomaly in all_anomalies:
                sensor = anomaly['sensor']
                sensor_anomaly_counts[sensor] = sensor_anomaly_counts.get(sensor, 0) + 1
            
            worst_sensor = max(sensor_anomaly_counts.keys(), key=sensor_anomaly_counts.get)
            insights.append(f"가장 많은 이상치: {worst_sensor} ({sensor_anomaly_counts[worst_sensor]}개)")
            
            # 심각도별 분류
            high_severity = len([a for a in all_anomalies if a['severity'] == 'high'])
            medium_severity = len([a for a in all_anomalies if a['severity'] == 'medium'])
            
            insights.append(f"심각도 - 높음: {high_severity}개, 보통: {medium_severity}개")
            
            # 최근 이상치
            recent_anomaly = top_anomalies[0]
            insights.append(f"최근 이상치: {recent_anomaly['sensor']} at {recent_anomaly['timestamp']}")
        
        return AnalysisResult(
            analysis_type="anomaly",
            title=f"이상치 탐지 분석 ({hours}시간)",
            description=f"통계적/ML 기반 이상치 {len(all_anomalies)}개 탐지",
            dataframe=df,
            anomalies=top_anomalies,
            insights=insights,
            confidence_score=0.8,
            data_quality_score=min(1.0, len(df) / (hours * 60))
        )
    
    async def _comprehensive_analysis(self, df: pd.DataFrame, sensors: List[str], hours: int) -> AnalysisResult:
        """종합 분석 (모든 분석 타입 결합)"""
        
        results = []
        
        # 각 분석 수행
        correlation_result = await self._analyze_correlations(df, sensors, hours)
        results.append(correlation_result)
        
        heatmap_result = await self._analyze_heatmaps(df, sensors, hours)  
        results.append(heatmap_result)
        
        anomaly_result = await self._analyze_anomalies(df, sensors, hours)
        results.append(anomaly_result)
        
        # 예측은 첫 번째 센서로
        prediction_result = await self._analyze_predictions(df, sensors, hours, target_sensor=sensors[0])
        results.append(prediction_result)
        
        # 종합 인사이트
        comprehensive_insights = []
        comprehensive_insights.append(f"=== 종합 분석 결과 ({hours}시간) ===")
        
        for result in results:
            comprehensive_insights.extend([f"[{result.analysis_type.upper()}] {insight}" for insight in result.insights[:2]])
        
        # 종합 데이터
        comprehensive_data = {
            'correlation': correlation_result.heatmap_data,
            'heatmap': heatmap_result.heatmap_data,
            'prediction': prediction_result.predictions,
            'anomalies': anomaly_result.anomalies[:5]  # 상위 5개만
        }
        
        return AnalysisResult(
            analysis_type="comprehensive",
            title=f"종합 데이터 분석 ({hours}시간)",
            description=f"{len(sensors)}개 센서 종합 분석 (상관성, 히트맵, 예측, 이상치)",
            dataframe=df,
            heatmap_data=comprehensive_data,
            insights=comprehensive_insights,
            confidence_score=0.85,
            data_quality_score=min(1.0, len(df) / (hours * 60))
        )
    
    async def _basic_statistical_analysis(self, df: pd.DataFrame, sensors: List[str], hours: int) -> AnalysisResult:
        """기본 통계 분석"""
        
        sensor_data = df[sensors].select_dtypes(include=[np.number])
        summary_stats = sensor_data.describe().round(3).to_dict()
        
        insights = []
        insights.append(f"{len(sensors)}개 센서 {hours}시간 기본 통계")
        insights.append(f"총 데이터 포인트: {len(df):,}개")
        
        for sensor in sensors:
            if sensor in summary_stats:
                mean_val = summary_stats[sensor]['mean']
                std_val = summary_stats[sensor]['std']
                cv = std_val / mean_val if mean_val != 0 else 0
                
                insights.append(f"{sensor}: 평균={mean_val:.2f}, 표준편차={std_val:.2f}, CV={cv:.3f}")
        
        return AnalysisResult(
            analysis_type="statistical",
            title=f"기본 통계 분석 ({hours}시간)",
            description=f"{len(sensors)}개 센서 기본 통계량",
            dataframe=df,
            summary_stats=summary_stats,
            insights=insights,
            confidence_score=0.9,
            data_quality_score=min(1.0, len(df) / (hours * 60))
        )


# 전역 분석 엔진
pandas_engine = PandasAnalysisEngine()


async def analyze_sensors_dynamic(
    sensors: List[str],
    analysis_type: str = "comprehensive",
    hours: int = 168,
    **kwargs
) -> AnalysisResult:
    """동적 센서 데이터 분석"""
    return await pandas_engine.analyze_sensor_data(sensors, analysis_type, hours, **kwargs)


async def quick_correlation_analysis(sensors: List[str], hours: int = 24) -> Dict:
    """빠른 상관성 분석"""
    result = await pandas_engine.analyze_sensor_data(sensors, "correlation", hours)
    return {
        'correlations': result.correlations,
        'insights': result.insights,
        'heatmap_data': result.heatmap_data
    }


async def predict_sensor_values(sensor: str, hours_ahead: int = 24) -> Dict:
    """센서 값 예측"""
    result = await pandas_engine.analyze_sensor_data([sensor], "prediction", 168, 
                                                   target_sensor=sensor, 
                                                   prediction_horizon=hours_ahead)
    return result.predictions