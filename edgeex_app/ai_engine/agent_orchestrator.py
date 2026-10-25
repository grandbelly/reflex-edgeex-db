"""
Multi-Agent RAG System Orchestrator
Medium 글 기반 다중 에이전트 구조 구현
"""

import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

from .rag_engine import RAGEngine
from .dynamic_rag_engine import DynamicRAGEngine
from .five_w1h_agent import FiveW1HAgent
import os
from openai import AsyncOpenAI
from ..queries.latest import latest_snapshot
from ..queries.qc import qc_rules


class AgentType(Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    REVIEW = "review"
    FIVE_W1H = "five_w1h"


@dataclass
class AgentContext:
    """에이전트 간 공유 컨텍스트"""
    query: str
    research_notes: Dict[str, str] = None
    analysis_result: str = ""
    review_feedback: str = ""
    sensor_data: List[Dict] = None
    qc_data: List[Dict] = None
    conflicts_detected: List[str] = None
    historical_data: Dict = None
    structured_response: str = ""  # 5W1H 구조화 응답
    five_w1h: Any = None  # 5W1H 응답 객체
    qc_violations: List[Dict] = None  # QC 위반 상세 정보
    data_source: str = "TimescaleDB"  # 데이터 소스
    view_used: str = ""  # 사용된 뷰
    time_range: str = ""  # 시간 범위
    needs_rework: bool = False  # 재작업 필요 여부
    
    def __post_init__(self):
        if self.research_notes is None:
            self.research_notes = {}
        if self.sensor_data is None:
            self.sensor_data = []
        if self.qc_data is None:
            self.qc_data = []
        if self.conflicts_detected is None:
            self.conflicts_detected = []
        if self.qc_violations is None:
            self.qc_violations = []


class BaseAgent:
    """기본 에이전트 클래스"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.rag_engine = None
    
    async def initialize(self, rag_engine: RAGEngine):
        """RAG 엔진 초기화"""
        self.rag_engine = rag_engine
    
    async def process(self, context: AgentContext) -> AgentContext:
        """에이전트별 처리 로직 (서브클래스에서 구현)"""
        raise NotImplementedError


class ResearchAgent(BaseAgent):
    """데이터 수집 및 연구 에이전트 (Dynamic RAG 통합)"""

    def __init__(self):
        super().__init__("ResearchAgent", "센서 데이터 및 도메인 지식 수집")
        self.dynamic_rag = None

    async def process(self, context: AgentContext) -> AgentContext:
        """연구 데이터 수집 및 메모 작성 (Dynamic RAG 활용)"""

        # Dynamic RAG를 통한 실시간 데이터 수집
        if self.dynamic_rag:
            try:
                # 자연어 쿼리를 통한 동적 데이터 수집
                result = await self.dynamic_rag.process_natural_language_query(context.query)

                if result and 'data' in result:
                    context.sensor_data = result['data']
                    context.view_used = result.get('metadata', {}).get('view_used', '')
                    context.time_range = result.get('metadata', {}).get('time_range', '')
                    context.research_notes["sensor_data"] = f"Dynamic RAG: {len(context.sensor_data)}개 데이터 수집"
                else:
                    # Fallback: 기존 방식
                    sensor_data = await latest_snapshot(None)
                    context.sensor_data = sensor_data or []
                    context.research_notes["sensor_data"] = f"총 {len(context.sensor_data)}개 최신 센서 데이터 수집"

            except Exception as e:
                # Fallback: 기존 방식
                sensor_data = await latest_snapshot(None)
                context.sensor_data = sensor_data or []
                context.research_notes["sensor_data"] = f"Fallback: {len(context.sensor_data)}개 데이터 수집"
        else:
            # 기본: 최신 센서 데이터 수집
            sensor_data = await latest_snapshot(None)
            context.sensor_data = sensor_data or []
            context.research_notes["sensor_data"] = f"총 {len(context.sensor_data)}개 최신 센서 데이터 수집"

        # 이력 데이터 질문인지 판단하여 추가 조회
        await self._collect_historical_data(context)

        # 2. QC 규칙 수집
        try:
            qc_data = await qc_rules(None)
            context.qc_data = qc_data or []
            context.research_notes["qc_rules"] = f"총 {len(context.qc_data)}개 QC 규칙 수집"
        except Exception as e:
            context.research_notes["qc_rules"] = f"QC 규칙 수집 실패: {e}"

        # 3. 도메인 지식 검색 (Dynamic RAG 또는 기존 RAG)
        if self.dynamic_rag:
            try:
                # Dynamic RAG의 semantic search 활용
                knowledge_results = await self.dynamic_rag.semantic_search(context.query, top_k=5)
                context.research_notes["domain_knowledge"] = f"Dynamic RAG: {len(knowledge_results)}개 지식 발견"

                for i, knowledge in enumerate(knowledge_results[:3]):
                    context.research_notes[f"knowledge_{i+1}"] = knowledge.get('content', '')[:100]

            except Exception as e:
                context.research_notes["domain_knowledge"] = f"Dynamic RAG 지식 검색 실패: {e}"
        elif self.rag_engine:
            try:
                knowledge_results = await self.rag_engine.semantic_search(context.query, top_k=5)
                context.research_notes["domain_knowledge"] = f"관련 지식 {len(knowledge_results)}개 발견"

                for i, knowledge in enumerate(knowledge_results):
                    context.research_notes[f"knowledge_{i+1}"] = (
                        f"[{knowledge.get('content_type', 'unknown')}] "
                        f"{knowledge.get('content', '')[:100]}..."
                    )
            except Exception as e:
                context.research_notes["domain_knowledge"] = f"지식 검색 실패: {e}"

        return context
    
    async def _collect_historical_data(self, context: AgentContext):
        """질문에 따라 이력 데이터 수집"""
        query_lower = context.query.lower()
        
        # 시간 관련 키워드 검출
        time_keywords = {
            '일주일': 7, '1주일': 7, '주일': 7,
            '어제': 1, '1일': 1, 
            '한달': 30, '1달': 30, '한 달': 30,
            '평균': 7, '총': 7, '개수': 7, '몇개': 7, '몇 개': 7
        }
        
        # 특정 센서 추출 (D101, D102 등)
        sensor_pattern = None
        for word in context.query.split():
            if word.startswith('D') and len(word) == 4 and word[1:].isdigit():
                sensor_pattern = word
                break
        
        # 시간 기간 결정
        days = None
        for keyword, period in time_keywords.items():
            if keyword in query_lower:
                days = period
                break
        
        if days and sensor_pattern:
            try:
                from datetime import datetime, timedelta
                from edgeex_app.db import q
                
                # 지정 기간의 이력 데이터 조회
                start_date = datetime.now() - timedelta(days=days)
                
                hist_query = '''
                SELECT COUNT(*) as count, MIN(ts) as start_time, MAX(ts) as end_time
                FROM public.influx_hist 
                WHERE tag_name = %s AND ts >= %s
                '''
                
                result = await q(hist_query, (sensor_pattern, start_date))
                if result and result[0]:
                    count = result[0]['count']
                    start_time = result[0]['start_time']
                    end_time = result[0]['end_time']
                    
                    context.historical_data = {
                        'sensor': sensor_pattern,
                        'period_days': days,
                        'count': count,
                        'start_time': start_time,
                        'end_time': end_time
                    }
                    
                    context.research_notes["historical_data"] = (
                        f"{sensor_pattern} 센서 {days}일간 이력 데이터: {count}개 "
                        f"(기간: {start_time} ~ {end_time})"
                    )
                    
            except Exception as e:
                context.research_notes["historical_data"] = f"이력 데이터 수집 실패: {e}"


class AnalysisAgent(BaseAgent):
    """분석 및 보고서 생성 에이전트 (Medium 글의 WriteAgent 모델링)"""
    
    def __init__(self):
        super().__init__("AnalysisAgent", "데이터 분석 및 인사이트 생성")
    
    async def process(self, context: AgentContext) -> AgentContext:
        """수집된 데이터를 바탕으로 분석 결과 생성"""
        
        analysis_parts = []
        
        # 1. 쿼리 분석
        analysis_parts.append(f"📋 **분석 요청**: {context.query}\n")
        
        # 2. 센서 상태 분석
        if context.sensor_data:
            analysis_parts.append("📊 **전체 센서 상태 분석**:")
            analysis_parts.append(f"총 {len(context.sensor_data)}개 센서 모니터링 중")
            
            # 모든 센서 상태 표시
            for sensor in context.sensor_data:
                tag = sensor.get('tag_name', 'Unknown')
                value = sensor.get('value', 'N/A')
                ts = sensor.get('ts', 'N/A')
                analysis_parts.append(f"- {tag}: {value} (최종 업데이트: {ts})")
            analysis_parts.append("")
        
        # 3. 연구 노트 요약
        if context.research_notes:
            analysis_parts.append("[RESEARCH] **연구 결과 요약**:")
            for note_key, note_value in context.research_notes.items():
                analysis_parts.append(f"- {note_key}: {note_value}")
            analysis_parts.append("")
        
        # 4. QC 상태 분석 (상세 정보 저장)
        if context.qc_data and context.sensor_data:
            violations = self._detect_qc_violations(context.sensor_data, context.qc_data)

            # QC 위반 상세 정보 저장 (5W1H Agent용)
            context.qc_violations = []
            qc_lookup = {rule.get('tag_name'): rule for rule in context.qc_data if rule.get('tag_name')}

            for sensor in context.sensor_data:
                tag_name = sensor.get('tag_name')
                value = sensor.get('value')
                if tag_name and value is not None and tag_name in qc_lookup:
                    qc_rule = qc_lookup[tag_name]
                    try:
                        val = float(value)
                        min_val = qc_rule.get('min_val')
                        max_val = qc_rule.get('max_val')
                        if min_val is not None and max_val is not None:
                            if val < float(min_val) or val > float(max_val):
                                context.qc_violations.append({
                                    'tag_name': tag_name,
                                    'value': val,
                                    'min_val': float(min_val),
                                    'max_val': float(max_val)
                                })
                    except (ValueError, TypeError):
                        pass

            if violations:
                analysis_parts.append("⚠️ **품질 관리 위반 사항**:")
                analysis_parts.append(f"총 {len(violations)}개의 위반사항 감지됨")
                for violation in violations:  # 모든 위반사항 표시
                    analysis_parts.append(f"- {violation}")
                analysis_parts.append("")
            else:
                analysis_parts.append("✅ **품질 관리 상태**: 모든 센서가 정상 범위 내에 있습니다.")
                analysis_parts.append("")
        
        context.analysis_result = "\n".join(analysis_parts)
        return context
    
    def _detect_qc_violations(self, sensor_data: List[Dict], qc_data: List[Dict]) -> List[str]:
        """QC 규칙 위반 감지 (상세 정보 포함)"""
        violations = []

        # QC 룩업 테이블 생성
        qc_lookup = {rule.get('tag_name'): rule for rule in qc_data if rule.get('tag_name')}

        for sensor in sensor_data:
            tag_name = sensor.get('tag_name')
            value = sensor.get('value')

            if not tag_name or value is None:
                continue

            qc_rule = qc_lookup.get(tag_name)
            if not qc_rule:
                continue

            try:
                val = float(value)
                # Critical 위반 체크
                crit_min = qc_rule.get('crit_min')
                crit_max = qc_rule.get('crit_max')
                min_val = qc_rule.get('min_val')
                max_val = qc_rule.get('max_val')

                if crit_min is not None and val < float(crit_min):
                    violations.append(f"🚨 {tag_name}: {value} (최소 임계값 {crit_min} 미만)")
                elif crit_max is not None and val > float(crit_max):
                    violations.append(f"🚨 {tag_name}: {value} (최대 임계값 {crit_max} 초과)")
                elif min_val is not None and val < float(min_val):
                    violations.append(f"⚠️ {tag_name}: {value} (최소 정상값 {min_val} 미만)")
                elif max_val is not None and val > float(max_val):
                    violations.append(f"⚠️ {tag_name}: {value} (최대 정상값 {max_val} 초과)")

            except (ValueError, TypeError):
                continue

        return violations


class ReviewAgent(BaseAgent):
    """검토 및 품질 보증 에이전트 (Medium 글의 ReviewAgent 모델링)"""
    
    def __init__(self):
        super().__init__("ReviewAgent", "결과 검토 및 모순 감지")
        self.conflict_patterns = [
            "어떤 상황에서도",
            "절대",
            "금지",
            "하지 마십시오",
            "WARNING", 
            "ERROR",
            "Alert"
        ]
    
    async def process(self, context: AgentContext) -> AgentContext:
        """분석 결과 검토 및 모순 사항 감지"""
        
        review_parts = []
        
        # 1. 기본 품질 검증
        if not context.analysis_result:
            context.review_feedback = "❌ 분석 결과가 비어있습니다. 다시 분석이 필요합니다."
            return context
        
        # 2. 모순 사항 감지 (Medium 글의 핵심 기능)
        conflicts = self._detect_conflicts(context)
        if conflicts:
            context.conflicts_detected = conflicts
            review_parts.append("⚠️ **모순 사항 감지**:")
            for conflict in conflicts:
                review_parts.append(f"- {conflict}")
            review_parts.append("")
        
        # 3. 데이터 완성도 검증
        completeness_score = self._calculate_completeness(context)
        review_parts.append(f"📊 **데이터 완성도**: {completeness_score:.1%}")
        
        # 4. 최종 승인 여부 
        approval_status = "✅ 승인됨" if completeness_score > 0.7 and not conflicts else "❌ 재작업 필요"
        review_parts.append(f"[REVIEW] **검토 결과**: {approval_status}")
        
        context.review_feedback = "\n".join(review_parts)
        return context
    
    def _detect_conflicts(self, context: AgentContext) -> List[str]:
        """모순 사항 자동 감지 (Medium 글의 핵심 로직)"""
        conflicts = []
        
        # 분석 결과에서 모순 패턴 검색
        analysis_text = context.analysis_result.lower()
        
        for pattern in self.conflict_patterns:
            if pattern.lower() in analysis_text:
                conflicts.append(f"모순 패턴 발견: '{pattern}'")
        
        return conflicts
    
    def _calculate_completeness(self, context: AgentContext) -> float:
        """데이터 완성도 계산"""
        score = 0.0
        max_score = 4.0
        
        if context.sensor_data:
            score += 1.0
        if context.qc_data:
            score += 1.0  
        if context.research_notes:
            score += 1.0
        if context.analysis_result:
            score += 1.0
            
        return score / max_score


class MultiAgentOrchestrator:
    """다중 에이전트 오케스트레이터 (Dynamic RAG & 5W1H 통합)"""

    def __init__(self):
        self.research_agent = ResearchAgent()
        self.analysis_agent = AnalysisAgent()
        self.review_agent = ReviewAgent()
        self.five_w1h_agent = FiveW1HAgent()  # 5W1H Agent 추가
        self.rag_engine = None
        self.dynamic_rag = None  # Dynamic RAG Engine
        self.openai_client = None
    
    async def initialize(self, rag_engine: RAGEngine):
        """모든 에이전트 초기화 (Dynamic RAG 통합)"""
        self.rag_engine = rag_engine

        # Dynamic RAG Engine 초기화
        try:
            self.dynamic_rag = DynamicRAGEngine()
            await self.dynamic_rag.initialize()
            print("✅ Dynamic RAG Engine 초기화 완료")

            # Research Agent에 Dynamic RAG 전달
            self.research_agent.dynamic_rag = self.dynamic_rag
        except Exception as e:
            print(f"⚠️ Dynamic RAG 초기화 실패 (기존 RAG 사용): {e}")
            self.dynamic_rag = None

        # 환경변수 강제 로드
        from edgeex_app.edgeex_app import load_env
        load_env()

        # OpenAI 클라이언트 초기화
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
            print("✅ Multi-Agent OpenAI 클라이언트 초기화 완료")

        # 각 에이전트 초기화
        await self.research_agent.initialize(rag_engine)
        await self.analysis_agent.initialize(rag_engine)
        await self.review_agent.initialize(rag_engine)
        # 5W1H Agent는 별도 초기화 불필요 (독립적)
    
    async def process_query(self, query: str) -> str:
        """Enhanced 워크플로우: Research → Analysis → Review → 5W1H"""

        # 초기 컨텍스트 생성
        context = AgentContext(query=query)

        try:
            # Dynamic RAG로 태그 발견 (사전 준비)
            if self.dynamic_rag:
                try:
                    print(f"[INFO] Dynamic RAG 태그 발견 중...")
                    await self.dynamic_rag.discover_tags()
                except Exception as e:
                    print(f"⚠️ 태그 발견 스킵: {e}")

            # 1단계: 연구 에이전트 (데이터 수집)
            print(f"🧠 ResearchAgent 실행 중...")
            context = await self.research_agent.process(context)

            # 2단계: 분석 에이전트 (보고서 생성)
            print(f"📝 AnalysisAgent 실행 중...")
            context = await self.analysis_agent.process(context)

            # 3단계: 검토 에이전트 (품질 보증)
            print(f"🔎 ReviewAgent 실행 중...")
            context = await self.review_agent.process(context)

            # 4단계: 5W1H 구조화 (6하원칙)
            print(f"📋 5W1H Agent 실행 중...")
            context = await self.five_w1h_agent.process(context)

            # 5W1H 구조화 응답이 있으면 우선 사용
            if context.structured_response:
                # OpenAI 보강 여부 결정
                if self.openai_client:
                    print(f"🤖 OpenAI로 5W1H 응답 보강 중...")
                    return await self._enhance_5w1h_with_openai(query, context)
                else:
                    print(f"✅ 5W1H 구조화 응답 반환")
                    return context.structured_response

            # Fallback: 기존 방식
            if self.openai_client:
                print(f"🤖 OpenAI 지능형 응답 생성 중...")
                return await self._generate_intelligent_response(query, context)
            else:
                print(f"⚠️ OpenAI 클라이언트 없음 - 템플릿 모드 사용")
                return await self._generate_template_response(context)

        except Exception as e:
            return f"❌ Multi-Agent 처리 중 오류 발생: {str(e)}"
    
    async def _generate_intelligent_response(self, query: str, context: AgentContext) -> str:
        """OpenAI를 사용한 지능형 응답 생성"""
        try:
            # 시스템 프롬프트 구성
            system_prompt = """당신은 산업용 센서 모니터링 시스템의 전문 AI 어시스턴트입니다.

다음 역할을 수행하세요:
1. 사용자의 질문을 정확히 이해하고 맞춤형 답변 제공
2. Multi-Agent 시스템이 수집한 전체 데이터를 기반으로 종합적인 분석 제공
3. 모든 센서 데이터와 QC 규칙을 고려한 상세한 인사이트 제공
4. 한국어로 친근하고 전문적인 답변 작성
5. 구체적인 센서 값, 임계값 위반, 권장사항을 명확히 제시

분석 요구사항:
- 전체 센서 상태를 종합적으로 분석
- QC 규칙과 실제 값을 비교하여 위반사항 식별
- 센서별 개별 상태와 전체 시스템 상태를 구분
- 이상 상황 발견시 구체적인 위험도와 대응방안 제시
- 트렌드나 패턴이 있다면 언급

응답 스타일:
- 질문에 직접적으로 답변
- 모든 관련 센서 데이터를 활용한 분석
- 수치적 근거와 함께 명확한 결론
- 실행 가능한 권장사항 제공"""

            # 컨텍스트 데이터 정리
            context_parts = []
            
            if context.sensor_data:
                context_parts.append(f"**전체 센서 데이터**: {len(context.sensor_data)}개")
                for sensor in context.sensor_data:
                    tag = sensor.get('tag_name', 'Unknown')
                    value = sensor.get('value', 'N/A')
                    ts = sensor.get('ts', 'N/A')
                    context_parts.append(f"- {tag}: {value} (업데이트: {ts})")
            
            if context.qc_data:
                context_parts.append(f"**QC 규칙**: {len(context.qc_data)}개 규칙 적용됨")
                for qc in context.qc_data:
                    tag = qc.get('tag_name', 'Unknown')
                    min_val = qc.get('min_val', 'N/A')
                    max_val = qc.get('max_val', 'N/A')
                    context_parts.append(f"- {tag} 규칙: 최소 {min_val}, 최대 {max_val}")
            
            if context.analysis_result:
                context_parts.append(f"**분석 결과**:\n{context.analysis_result}")
            
            if context.review_feedback:
                context_parts.append(f"**검토 결과**:\n{context.review_feedback}")
            
            if context.historical_data:
                hist = context.historical_data
                context_parts.append(f"**이력 데이터**: {hist['sensor']} 센서의 {hist['period_days']}일간 데이터 {hist['count']}개 (기간: {hist['start_time']} ~ {hist['end_time']})")

            user_prompt = f"""사용자 질문: {query}

수집된 데이터:
{chr(10).join(context_parts)}

위 정보를 바탕으로 사용자의 질문에 정확하고 유용한 답변을 제공해주세요."""

            print(f"🔗 OpenAI API 호출 중... (모델: gpt-3.5-turbo)")
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            openai_response = response.choices[0].message.content.strip()
            print(f"✅ OpenAI 응답 수신 완료 (길이: {len(openai_response)} 문자)")
            
            # 시각화 데이터 생성
            from edgeex_app.ai_engine.visualization_generator import generate_visualization_data, format_visualization_response
            
            viz_data = await generate_visualization_data(
                query, 
                context.sensor_data, 
                context.qc_data, 
                context.historical_data
            )
            
            if viz_data:
                print(f"📊 시각화 데이터 생성 완료: {list(viz_data.keys())}")
                return format_visualization_response(openai_response, viz_data)
            
            return openai_response
            
        except Exception as e:
            print(f"❌ OpenAI 응답 생성 실패: {e}")
            # Fallback to template response
            return await self._generate_template_response(context)

    async def _enhance_5w1h_with_openai(self, query: str, context: AgentContext) -> str:
        """5W1H 구조화 응답을 OpenAI로 보강"""
        try:
            system_prompt = """당신은 6하원칙(5W1H) 기반 응답을 보강하는 전문가입니다.
주어진 구조화된 정보를 바탕으로 더 자연스럽고 통찰력 있는 응답을 생성하세요.
기존 5W1H 구조를 유지하면서 설명을 풍부하게 만드세요."""

            user_prompt = f"""질문: {query}

6하원칙 분석 결과:
{context.structured_response}

위 분석을 더 자연스럽고 통찰력 있게 보강해주세요."""

            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=800
            )

            enhanced = response.choices[0].message.content.strip()

            # 시각화 데이터 추가
            from edgeex_app.ai_engine.visualization_generator import generate_visualization_data, format_visualization_response

            viz_data = await generate_visualization_data(
                query,
                context.sensor_data,
                context.qc_data,
                context.historical_data
            )

            if viz_data:
                return format_visualization_response(enhanced, viz_data)

            return enhanced

        except Exception as e:
            print(f"⚠️ OpenAI 보강 실패, 원본 5W1H 응답 반환: {e}")
            return context.structured_response

    async def _generate_template_response(self, context: AgentContext) -> str:
        """템플릿 기반 응답 생성 (OpenAI 사용 불가시 대체)"""
        response_parts = []
        
        response_parts.append("🤖 **센서 데이터 분석 결과**\n")
        
        if context.analysis_result:
            response_parts.append(context.analysis_result)
        else:
            response_parts.append("분석 데이터를 가져올 수 없습니다.")
        
        if context.review_feedback:
            response_parts.append("\n---\n")
            response_parts.append("🔍 **검토 의견**\n")
            response_parts.append(context.review_feedback)
        
        return "\n".join(response_parts)


# 전역 오케스트레이터 인스턴스
orchestrator = MultiAgentOrchestrator()


async def initialize_multi_agent_system(rag_engine: RAGEngine):
    """Multi-Agent 시스템 초기화"""
    await orchestrator.initialize(rag_engine)


async def get_multi_agent_response(query: str) -> str:
    """Multi-Agent RAG 응답 생성"""
    # Orchestrator 초기화 확인
    if not orchestrator.openai_client:
        from edgeex_app.ai_engine.rag_engine import rag_engine, initialize_rag_engine
        
        # RAG 엔진 초기화
        if not rag_engine.openai_client:
            await initialize_rag_engine()
        
        # Multi-Agent 시스템 초기화
        await initialize_multi_agent_system(rag_engine)
        print("✅ Multi-Agent 시스템 자동 초기화 완료")
    
    return await orchestrator.process_query(query)