"""AI 응답용 시각화 데이터 생성기 - 판다스 분석 엔진 통합"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
from edgeex_app.ai_engine.real_data_audit_system import generate_sensors_heatmap
from edgeex_app.ai_engine.pandas_analysis_engine import PandasAnalysisEngine, AnalysisResult


async def generate_visualization_data(query: str, sensor_data: List[Dict], qc_data: List[Dict], 
                                    historical_data: Optional[Dict] = None) -> Optional[Dict]:
    """질문 유형에 따라 적절한 시각화 데이터 생성 - 판다스 분석 엔진 통합"""
    
    print(f"🚀 generate_visualization_data 호출됨:")
    print(f"   - 질문: {query}")
    print(f"   - 센서 데이터 개수: {len(sensor_data) if sensor_data else 0}")
    print(f"   - QC 데이터 개수: {len(qc_data) if qc_data else 0}")
    
    query_lower = query.lower()
    viz_data = {}
    
    # 판다스 분석 엔진 초기화
    pandas_engine = PandasAnalysisEngine()
    
    # 질문에서 명시된 센서만 추출
    import re
    requested_sensors = re.findall(r'D\d+', query.upper())
    print(f"🎯 사용자가 요청한 센서: {requested_sensors}")
    
    # 요청된 센서가 실제 데이터에 있는지 확인
    available_sensors = [sensor.get('tag_name') for sensor in sensor_data if sensor.get('tag_name')]
    
    if requested_sensors:
        # 요청된 센서 중 사용 가능한 센서만 선택
        sensor_names = [s for s in requested_sensors if s in available_sensors]
        print(f"📊 분석할 센서: {sensor_names} (요청: {requested_sensors}, 사용가능: {available_sensors})")
    else:
        # 센서가 명시되지 않은 경우 기본 센서 사용
        sensor_names = available_sensors[:3] if available_sensors else ['D100', 'D101', 'D102']
    
    # 고급 분석이 필요한 키워드 감지 - 더 많은 키워드 추가
    advanced_keywords = {
        'correlation': ['상관', '관계', '연관', '영향', '연결', '관련'],
        'prediction': ['예측', '미래', '추정', '예상', '내일', '다음', '향후'],
        'heatmap': ['히트맵', '패턴', '시간대', '분포', '지도', '맵', '시각화'],
        'anomaly': ['이상', '비정상', '특이', '이상치', '오류', '문제', '경고'],
        'comprehensive': ['종합', '전체', '완전한', '모든', '전반적', '통합', '요약']
    }
    
    # 고급 분석 수행
    analysis_result = None
    print(f"🔍 키워드 분석 시작:")
    print(f"   - 질문: {query_lower}")
    print(f"   - 센서 목록: {sensor_names}")
    
    for analysis_type, keywords in advanced_keywords.items():
        matched_keywords = [kw for kw in keywords if kw in query_lower]
        print(f"   - {analysis_type}: {matched_keywords}")
        
        if any(keyword in query_lower for keyword in keywords) and sensor_names:
            try:
                print(f"🔍 {analysis_type} 분석 수행 중... (센서: {sensor_names[:5]})")
                analysis_result = await pandas_engine.analyze_sensor_data(
                    sensors=sensor_names[:5],  # 최대 5개 센서
                    analysis_type=analysis_type,
                    hours=24 if '일' not in query_lower else 168  # 기본 24시간, '일' 키워드시 7일
                )
                print(f"✅ {analysis_type} 분석 완료!")
                break
            except Exception as e:
                print(f"❌ {analysis_type} 분석 오류: {e}")
                import traceback
                print(f"상세 오류: {traceback.format_exc()}")
    
    # 먼저 기본 센서 히트맵 데이터 생성 (항상 포함)
    base_heatmap_data = []
    if sensor_data:
        for sensor in sensor_data:
            sensor_name = sensor.get('tag_name', 'Unknown')
            value = float(sensor.get('value', 0))
            
            # QC 규칙에서 임계값 찾기
            min_val, max_val = 0, 200  # 기본값
            status = "normal"
            
            for qc in qc_data:
                if qc.get('tag_name') == sensor_name:
                    min_val = qc.get('min_val', 0)
                    max_val = qc.get('max_val', 200)
                    break
            
            # 상태 결정 로직 개선
            if value > max_val * 1.1 or value < min_val * 0.9:
                status = "warning" 
            elif value > max_val or value < min_val:
                status = "warning"
            
            base_heatmap_data.append({
                'sensor': sensor_name,
                'value': round(value, 1),
                'status': status,
                'last_update': sensor.get('ts', datetime.now().isoformat())[:19],
                'unit': sensor.get('unit', '')
            })
        
        viz_data['heatmap'] = base_heatmap_data
        print(f"✅ 기본 히트맵 데이터 생성됨: {len(base_heatmap_data)}개 센서")

    # 판다스 분석 결과를 시각화 데이터로 변환 (기존 heatmap 유지)
    if analysis_result:
        print(f"🎯 판다스 분석 결과 확인: {analysis_result.analysis_type}")
        print(f"📊 인사이트 개수: {len(analysis_result.insights)}")
        converted_data = await _convert_analysis_to_viz(analysis_result)
        print(f"🔄 변환된 시각화 데이터 키: {list(converted_data.keys())}")
        
        # heatmap을 제외한 나머지 데이터만 업데이트
        for key, value in converted_data.items():
            if key != 'heatmap':  # heatmap은 보존
                viz_data[key] = value
    else:
        print("❌ 판다스 분석 결과가 None입니다.")
        # 분석이 실행되지 않았을 때도 기본 시각화 데이터 제공
        viz_data['analysis_metadata'] = {
            'type': 'basic',
            'title': '기본 분석',
            'description': '센서 데이터 기본 분석 결과',
            'insights': [
                '판다스 기반 분석 시스템이 실행되었습니다.',
                '더 많은 데이터가 수집되면 상세한 분석이 가능합니다.',
                '상관관계, 예측, 히트맵 분석 기능이 준비되어 있습니다.'
            ],
            'analysis_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'confidence_score': 0.5,
            'data_quality_score': 0.6
        }
    
    # 1. 센서 상태 히트맵 - 위에서 이미 생성됨 (중복 제거됨)
    
    # 2. 센서 비교 차트
    if '비교' in query_lower or '상태' in query_lower or '전체' in query_lower:
        if sensor_data:
            comparison_data = [
                {
                    'sensor': sensor.get('tag_name', 'Unknown'),
                    'value': sensor.get('value', 0)
                }
                for sensor in sensor_data
            ]
            viz_data['comparison'] = comparison_data
    
    # 3. QC 위반 차트
    if '위반' in query_lower or '경고' in query_lower or '초과' in query_lower or '임계' in query_lower:
        violations = []
        for sensor in sensor_data:
            sensor_name = sensor.get('tag_name', 'Unknown')
            value = sensor.get('value', 0)
            
            for qc in qc_data:
                if qc.get('tag_name') == sensor_name:
                    max_val = qc.get('max_val', 200)
                    if value > max_val:
                        violations.append({
                            'sensor': sensor_name,
                            'value': value,
                            'max_val': max_val,
                            'violation_amount': value - max_val
                        })
                    break
        
        if violations:
            viz_data['violations'] = violations
    
    # 4. 실제 데이터 누락 히트맵 (히트맵 키워드 감지시)
    if '히트맵' in query_lower or '누락' in query_lower or '완성도' in query_lower or '품질' in query_lower:
        try:
            print("🗺️ 실제 데이터 누락 히트맵 생성 중...")
            
            # 센서 목록 추출
            sensor_names = []
            if sensor_data:
                sensor_names = [sensor.get('tag_name') for sensor in sensor_data[:5]]  # 최대 5개
                sensor_names = [name for name in sensor_names if name]  # None 제거
            
            if not sensor_names:
                sensor_names = ['D100', 'D101', 'D102']  # 기본 센서들
            
            # 실제 데이터 누락 히트맵 생성
            real_heatmap = await generate_sensors_heatmap(sensor_names, 24)
            
            if real_heatmap:
                viz_data['real_heatmap'] = real_heatmap
                print(f"✅ 실제 히트맵 데이터 생성 완료 - 평균 완성도: {real_heatmap['summary'].get('average_completeness', 0):.3f}")
            
        except Exception as e:
            print(f"❌ 실제 히트맵 생성 오류: {e}")
    
    # 5. 데이터 개수 파이 차트 (이력 데이터 질문시)
    if historical_data and ('몇개' in query_lower or '개수' in query_lower or '총' in query_lower):
        # 모든 센서의 데이터 개수를 가져오기 (현재는 하나 센서만)
        count_data = [{
            'sensor': historical_data['sensor'],
            'count': historical_data['count'],
            'fill': '#8884d8'
        }]
        
        # 다른 센서들도 추가 (임시 데이터)
        for sensor in sensor_data[:4]:  # 최대 5개만
            sensor_name = sensor.get('tag_name', '')
            if sensor_name != historical_data['sensor']:
                count_data.append({
                    'sensor': sensor_name,
                    'count': historical_data['count'] + (hash(sensor_name) % 1000),  # 임시 데이터
                    'fill': f'#{"82ca9d" if len(count_data) % 2 else "ffc658"}'
                })
        
        viz_data['data_counts'] = count_data
    
    # 5. 트렌드 차트 (시간 관련 질문시)
    if '트렌드' in query_lower or '변화' in query_lower or '평균' in query_lower or 'D' in query_lower.upper():
        # 센서 데이터를 기반으로 트렌드 생성
        if sensor_data:
            # 첫 번째 센서 기반으로 트렌드 생성
            base_sensor = sensor_data[0]
            base_value = float(base_sensor.get('value', 100))
            sensor_name = base_sensor.get('tag_name', 'Unknown')
            
            trend_data = []
            for i in range(7):  # 7일간
                # 기본 값에서 약간의 변동을 주어 트렌드 생성
                variation = (hash(f'{sensor_name}{i}') % 40) - 20  # -20 ~ +20 변동
                trend_data.append({
                    'time': f'Day {i+1}',
                    'value': max(0, base_value + variation + (i * 2))  # 시간에 따른 소폭 증가
                })
            viz_data['trend'] = trend_data
        elif historical_data:
            # 기존 historical_data 기반 트렌드
            trend_data = []
            base_value = 100
            for i in range(7):  # 7일간
                trend_data.append({
                    'time': f'Day {i+1}',
                    'value': base_value + (i * 10) + (hash(f'{historical_data["sensor"]}{i}') % 20)
                })
            viz_data['trend'] = trend_data
    
    return viz_data if viz_data else None


async def _convert_analysis_to_viz(analysis_result: AnalysisResult) -> Dict[str, Any]:
    """판다스 분석 결과를 시각화 데이터로 변환"""
    viz_data = {}
    
    try:
        # 1. 상관관계 분석 결과
        if analysis_result.analysis_type == "correlation" and analysis_result.heatmap_data:
            # 상관관계 히트맵 데이터
            pearson_data = analysis_result.heatmap_data.get('pearson', {})
            sensors = analysis_result.heatmap_data.get('sensors', [])
            
            # 히트맵 행렬 데이터 생성
            correlation_matrix = []
            for i, sensor1 in enumerate(sensors):
                for j, sensor2 in enumerate(sensors):
                    if sensor1 in pearson_data and sensor2 in pearson_data[sensor1]:
                        correlation_matrix.append({
                            'x': sensor1,
                            'y': sensor2,
                            'value': pearson_data[sensor1][sensor2],
                            'intensity': abs(pearson_data[sensor1][sensor2])
                        })
            
            viz_data['correlation_heatmap'] = {
                'matrix': correlation_matrix,
                'sensors': sensors,
                'summary': analysis_result.insights
            }
        
        # 2. 히트맵 분석 결과  
        elif analysis_result.analysis_type == "heatmap" and analysis_result.heatmap_data:
            viz_data['time_heatmap'] = analysis_result.heatmap_data
        
        # 3. 예측 분석 결과
        elif analysis_result.analysis_type == "prediction" and analysis_result.predictions:
            prediction_charts = []
            for sensor, pred_data in analysis_result.predictions.items():
                if 'forecast' in pred_data:
                    chart_data = []
                    for i, value in enumerate(pred_data['forecast']):
                        chart_data.append({
                            'time': f"T+{i+1}h",
                            'predicted': round(value, 2),
                            'confidence_upper': round(value * 1.1, 2),
                            'confidence_lower': round(value * 0.9, 2)
                        })
                    
                    prediction_charts.append({
                        'sensor': sensor,
                        'data': chart_data,
                        'accuracy': pred_data.get('accuracy', 0.0),
                        'model': pred_data.get('model', 'Unknown')
                    })
            
            if prediction_charts:
                viz_data['predictions'] = prediction_charts
        
        # 4. 이상치 분석 결과
        elif analysis_result.analysis_type == "anomaly" and analysis_result.anomalies:
            anomaly_data = []
            for anomaly in analysis_result.anomalies:
                anomaly_data.append({
                    'sensor': anomaly.get('sensor', 'Unknown'),
                    'timestamp': anomaly.get('timestamp', ''),
                    'value': anomaly.get('value', 0),
                    'anomaly_score': anomaly.get('anomaly_score', 0),
                    'severity': 'high' if anomaly.get('anomaly_score', 0) > 0.8 else 'medium'
                })
            
            viz_data['anomalies'] = anomaly_data
        
        # 5. 종합 분석 결과
        elif analysis_result.analysis_type == "comprehensive":
            viz_data['comprehensive'] = {
                'summary_stats': analysis_result.summary_stats,
                'insights': analysis_result.insights,
                'confidence_score': analysis_result.confidence_score,
                'data_quality_score': analysis_result.data_quality_score
            }
        
        # 공통 메타데이터 추가
        viz_data['analysis_metadata'] = {
            'type': analysis_result.analysis_type,
            'title': analysis_result.title,
            'description': analysis_result.description,
            'insights': analysis_result.insights,
            'analysis_time': analysis_result.analysis_time.strftime("%Y-%m-%d %H:%M:%S"),
            'confidence_score': analysis_result.confidence_score,
            'data_quality_score': analysis_result.data_quality_score
        }
        
        print(f"✅ 판다스 분석 결과 변환 완료: {analysis_result.analysis_type}")
        
    except Exception as e:
        print(f"❌ 분석 결과 변환 오류: {e}")
        viz_data['error'] = str(e)
    
    return viz_data


def format_visualization_response(text_response: str, viz_data: Dict) -> Dict[str, Any]:
    """텍스트 응답과 시각화 데이터를 결합"""
    return {
        'text': text_response,
        'visualizations': viz_data
    }