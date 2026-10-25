"""
Real RAG (Retrieval-Augmented Generation) Engine
진짜 RAG 시스템 - 의미론적 검색 및 컨텍스트 기반 응답 생성
"""

import json
import asyncio
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# OpenAI integration
from openai import AsyncOpenAI

# Text processing and similarity  
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Database and existing modules
from ..queries.latest import latest_snapshot
from ..queries.qc import qc_rules  
from .knowledge_builder import search_knowledge, get_sensor_knowledge
from .hallucination_prevention import HallucinationPrevention, ValidationResult
from .w5h1_formatter import W5H1Formatter, W5H1Response


class RAGEngine:
    """진짜 RAG 엔진 - 의미론적 검색 및 컨텍스트 기반 응답 생성"""
    
    def __init__(self):
        self.vectorizer = None
        self.knowledge_cache = []
        self.last_cache_update = None
        self.openai_client = None
        self.hallucination_prevention = None
        self.w5h1_formatter = W5H1Formatter()
        self._initialized = False  # lazy-init 가드 (get_rag_response 첫 호출 시 1회 init)

    async def initialize(self):
        """RAG 엔진 초기화"""
        # 환경변수 강제 로드
        from edgeex_app.edgeex_app import load_env
        load_env()
        
        # 보안 설정에서 API 키 가져오기
        from ..utils.secure_config import get_api_key_manager
        api_manager = get_api_key_manager()
        api_key = api_manager.get_openai_key()
        
        # OpenAI 클라이언트 초기화
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
            masked_key = api_manager.secure_config.mask_api_key(api_key)
            print(f"✅ OpenAI 클라이언트 초기화 완료 (키: {masked_key})")
        else:
            print("⚠️ OpenAI API 키가 없습니다. 템플릿 모드로 동작합니다.")
        
        # 할루시네이션 방지 시스템 초기화
        db_dsn = os.getenv('TS_DSN', 'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable')
        self.hallucination_prevention = HallucinationPrevention(db_dsn)
        print("🛡️ 할루시네이션 방지 시스템 초기화 완료")
            
        await self._update_knowledge_cache()
        self._initialized = True
        print("🧠 RAG 엔진 초기화 완료")
        
    async def _update_knowledge_cache(self):
        """지식베이스 캐시 업데이트"""
        try:
            # 모든 지식 로드
            from ..db import q
            sql = "SELECT id, content, content_type, metadata FROM ai_engine.knowledge_base ORDER BY created_at"
            knowledge_data = await q(sql, ())
            
            if knowledge_data:
                self.knowledge_cache = knowledge_data
                
                # TF-IDF 벡터화
                texts = [item['content'] for item in knowledge_data]
                self.vectorizer = TfidfVectorizer(
                    max_features=1000,
                    stop_words='english',
                    ngram_range=(1, 2)
                )
                self.vectorizer.fit(texts)
                
                self.last_cache_update = datetime.now()
                print(f"📚 지식베이스 캐시 업데이트: {len(knowledge_data)}개 항목")
            else:
                print("📚 지식베이스 테이블이 비어있습니다. OpenAI 모드로 동작합니다.")
                
        except Exception as e:
            print(f"📚 지식베이스 캐시 업데이트 실패 (정상): {e}")
            print("📚 OpenAI 전용 모드로 동작합니다.")
            # 테이블이 없어도 계속 진행
            
    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """의미론적 검색 - TF-IDF 기반 유사도 계산"""
        print(f"\n🔍 [RAG] semantic_search 시작: query='{query}', top_k={top_k}")
        
        if not self.vectorizer or not self.knowledge_cache:
            print(f"📚 [RAG] 캐시 업데이트 필요 - vectorizer: {self.vectorizer is not None}, cache: {len(self.knowledge_cache) if self.knowledge_cache else 0}")
            await self._update_knowledge_cache()
            
        if not self.knowledge_cache:
            print(f"⚠️ [RAG] 지식베이스 캐시 비어있음")
            return []
            
        try:
            # 쿼리 벡터화
            print(f"🔢 [RAG] 쿼리 벡터화 중...")
            query_vector = self.vectorizer.transform([query])
            print(f"   벡터 형태: {query_vector.shape}, 0이 아닌 값: {query_vector.nnz}")
            
            # 모든 지식 벡터화  
            texts = [item['content'] for item in self.knowledge_cache]
            print(f"📚 [RAG] 지식베이스 벡터화: {len(texts)}개 항목")
            knowledge_vectors = self.vectorizer.transform(texts)
            
            # 코사인 유사도 계산
            similarities = cosine_similarity(query_vector, knowledge_vectors)[0]
            print(f"📊 [RAG] 유사도 계산 완료: min={similarities.min():.3f}, max={similarities.max():.3f}, mean={similarities.mean():.3f}")
            
            # 상위 K개 결과 추출
            top_indices = np.argsort(similarities)[::-1][:top_k]
            print(f"🎯 [RAG] 상위 {top_k}개 인덱스: {top_indices.tolist()}")
            
            results = []
            for idx in top_indices:
                sim_score = float(similarities[idx])
                if sim_score > 0.1:  # 최소 유사도 임계값
                    item = self.knowledge_cache[idx].copy()
                    item['similarity_score'] = sim_score
                    results.append(item)
                    print(f"   ✅ 포함: idx={idx}, 유사도={sim_score:.3f}, 타입={item.get('content_type')}")
                else:
                    print(f"   ❌ 제외: idx={idx}, 유사도={sim_score:.3f} (임계값 0.1 미달)")
            
            print(f"🔍 [RAG] semantic_search 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            print(f"❌ [RAG] semantic_search 실패: {e}")
            import traceback
            print(traceback.format_exc())
            return []
            
    async def extract_sensor_tags(self, query: str) -> List[str]:
        """쿼리에서 센서 태그 추출"""
        print(f"\n🏷️ [RAG] extract_sensor_tags: query='{query}'")
        import re
        
        # D + 숫자 패턴 매칭
        pattern = r'D\d{3}'
        matches = re.findall(pattern, query.upper())
        print(f"   패턴 매칭 결과: {matches}")
        
        # 일반적인 센서 언급도 포함
        sensor_keywords = {
            '온도': ['D100'],
            '압력': ['D101'], 
            '유량': ['D102'],
            '진동': ['D200'],
            '전력': ['D300']
        }
        
        for keyword, tags in sensor_keywords.items():
            if keyword in query:
                print(f"   키워드 '{keyword}' 발견 -> 태그 추가: {tags}")
                matches.extend(tags)
        
        unique_tags = list(set(matches))  # 중복 제거
        print(f"🏷️ [RAG] 추출된 센서 태그: {unique_tags}")
        return unique_tags
        
    async def build_context(self, query: str) -> Dict[str, Any]:
        """질문에 대한 종합적인 컨텍스트 구성"""
        print(f"\n📋 [RAG] build_context 시작: query='{query}'")
        
        context = {
            "query": query,
            "sensor_tags": [],
            "current_data": [],
            "qc_rules": [], 
            "relevant_knowledge": [],
            "sensor_specific_knowledge": [],
            "sensor_metadata": {}  # 센서 타입과 단위 정보
        }
        
        try:
            # 1. 센서 태그 추출
            context["sensor_tags"] = await self.extract_sensor_tags(query)
            print(f"📋 [RAG] 1단계 완료 - 센서 태그: {context['sensor_tags']}")
            
            # 1.5. 센서 메타데이터 설정
            for tag in context["sensor_tags"]:
                if tag == 'D100':
                    context["sensor_metadata"][tag] = {'type': 'temperature', 'unit': '°C', 'name': '온도'}
                elif tag == 'D101':
                    context["sensor_metadata"][tag] = {'type': 'pressure', 'unit': 'bar', 'name': '압력'}
                elif tag == 'D102':
                    context["sensor_metadata"][tag] = {'type': 'flow', 'unit': 'L/min', 'name': '유량'}
                elif tag.startswith('D2'):
                    context["sensor_metadata"][tag] = {'type': 'vibration', 'unit': 'mm/s', 'name': '진동'}
                elif tag.startswith('D3'):
                    context["sensor_metadata"][tag] = {'type': 'power', 'unit': '%', 'name': '전력'}
            
            # 2. 현재 센서 데이터 조회
            if context["sensor_tags"]:
                print(f"📊 [RAG] 2단계 - 특정 센서 데이터 조회 중...")
                for tag in context["sensor_tags"]:
                    sensor_data = await latest_snapshot(tag)
                    if sensor_data:
                        context["current_data"].extend(sensor_data)
                        print(f"   {tag}: {len(sensor_data)}개 데이터")
                    else:
                        print(f"   {tag}: 데이터 없음")
            else:
                # 전체 데이터 조회
                print(f"📊 [RAG] 2단계 - 전체 센서 데이터 조회 중...")
                all_data = await latest_snapshot(None)
                context["current_data"] = all_data[:10] if all_data else []
                print(f"   전체 데이터: {len(context['current_data'])}개")
                
            # 3. QC 규칙 조회
            if context["sensor_tags"]:
                print(f"⚖️ [RAG] 3단계 - QC 규칙 조회 중...")
                for tag in context["sensor_tags"]:
                    qc_data = await qc_rules(tag)
                    if qc_data:
                        context["qc_rules"].extend(qc_data)
                        print(f"   {tag}: {len(qc_data)}개 QC 규칙")
                    else:
                        print(f"   {tag}: QC 규칙 없음")
            
            # 4. 의미론적 지식 검색
            print(f"🧠 [RAG] 4단계 - 의미론적 지식 검색 중...")
            context["relevant_knowledge"] = await self.semantic_search(query, top_k=5)
            print(f"   관련 지식: {len(context['relevant_knowledge'])}개")
            
            # 5. 센서별 특화 지식
            if context["sensor_tags"]:
                print(f"🔧 [RAG] 5단계 - 센서별 특화 지식 조회 중...")
                for tag in context["sensor_tags"]:
                    sensor_knowledge = await get_sensor_knowledge(tag)
                    if sensor_knowledge:
                        context["sensor_specific_knowledge"].extend(sensor_knowledge)
                        print(f"   {tag}: {len(sensor_knowledge)}개 특화 지식")
                    else:
                        print(f"   {tag}: 특화 지식 없음")
                    
        except Exception as e:
            print(f"❌ [RAG] build_context 실패: {e}")
            import traceback
            print(traceback.format_exc())
        
        print(f"📋 [RAG] build_context 완료:")
        print(f"   - 센서 태그: {len(context['sensor_tags'])}개")
        print(f"   - 현재 데이터: {len(context['current_data'])}개")
        print(f"   - QC 규칙: {len(context['qc_rules'])}개")
        print(f"   - 관련 지식: {len(context['relevant_knowledge'])}개")
        print(f"   - 특화 지식: {len(context['sensor_specific_knowledge'])}개")
        
        return context
        
    def _format_context_for_llm(self, context: Dict[str, Any]) -> str:
        """LLM을 위한 컨텍스트 포맷팅"""
        
        formatted = f"사용자 질문: {context['query']}\n\n"
        
        # 현재 센서 데이터
        if context["current_data"]:
            formatted += "📊 현재 센서 데이터:\n"
            for data in context["current_data"][:5]:  # 최대 5개만
                tag = data.get('tag_name', 'Unknown')
                value = data.get('value', 'N/A')
                ts = data.get('ts', 'N/A')
                formatted += f"- {tag}: {value} (시간: {ts})\n"
            formatted += "\n"
            
        # 관련 지식
        if context["relevant_knowledge"]:
            formatted += "🧠 관련 도메인 지식:\n"
            for knowledge in context["relevant_knowledge"]:
                score = knowledge.get('similarity_score', 0)
                content = knowledge.get('content', '')
                formatted += f"- (유사도: {score:.2f}) {content}\n"
            formatted += "\n"
            
        # 센서별 전문 지식
        if context["sensor_specific_knowledge"]:
            formatted += "🔧 센서 전문 지식:\n"
            for knowledge in context["sensor_specific_knowledge"]:
                content_type = knowledge.get('content_type', '')
                content = knowledge.get('content', '')
                formatted += f"- [{content_type}] {content}\n"
            formatted += "\n"
            
        # QC 규칙
        if context["qc_rules"]:
            formatted += "⚖️ 품질 관리 규칙:\n"
            for rule in context["qc_rules"]:
                tag = rule.get('tag_name', '')
                min_val = rule.get('min_val', 'N/A')
                max_val = rule.get('max_val', 'N/A') 
                formatted += f"- {tag}: 범위 {min_val} ~ {max_val}\n"
                
        return formatted
        
    async def generate_response(self, query: str, use_w5h1: bool = True) -> str:
        """RAG 기반 응답 생성
        
        Args:
            query: 사용자 질문
            use_w5h1: 6하원칙 포맷 사용 여부
        """
        
        try:
            # 1. 컨텍스트 구성
            context = await self.build_context(query)
            
            # 2. 규칙 기반 빠른 응답 (특정 패턴)
            quick_response = await self._try_quick_response(query, context)
            if quick_response:
                # 6하원칙 포맷팅 적용
                if use_w5h1:
                    quick_response = self.w5h1_formatter.format_response(
                        quick_response, 
                        question=query,
                        context=context,
                        format_type='markdown'
                    )
                return quick_response
                
            # 3. LLM 기반 응답 생성
            response = await self._generate_contextual_response(query, context)
            
            # 4. 6하원칙 포맷팅 적용
            if use_w5h1:
                response = self.w5h1_formatter.format_response(
                    response,
                    question=query,
                    context=context,
                    format_type='markdown'
                )
            
            return response
            
        except Exception as e:
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"
            
    async def _try_quick_response(self, query: str, context: Dict[str, Any]) -> Optional[str]:
        """규칙 기반 빠른 응답 시도"""
        
        query_lower = query.lower()
        
        # 현재 상태 질문
        if any(word in query_lower for word in ['현재', '상태', 'current', 'status']):
            if context["sensor_tags"]:
                return self._format_current_status_response(context)
                
        # 경고/알람 질문  
        if any(word in query_lower for word in ['경고', '알람', '위험', '이상', 'alert', 'warning']):
            return self._format_alert_response(context)
            
        # 도움말/사용법
        if any(word in query_lower for word in ['도움', '도움말', '사용법', 'help']):
            return self._format_help_response()
            
        return None
        
    def _format_current_status_response(self, context: Dict[str, Any]) -> str:
        """현재 상태 응답 포맷"""
        
        if not context["current_data"]:
            return "현재 센서 데이터를 가져올 수 없습니다."
            
        response = "📊 현재 센서 상태:\n\n"
        
        for data in context["current_data"][:5]:
            tag = data.get('tag_name', 'Unknown')
            value = data.get('value', 'N/A') 
            ts = data.get('ts', 'N/A')
            
            # 관련 지식 찾기
            sensor_info = ""
            for knowledge in context["sensor_specific_knowledge"]:
                if knowledge.get('metadata', {}).get('sensor_tag') == tag:
                    if knowledge.get('content_type') == 'sensor_spec':
                        sensor_info = f" - {knowledge['content'][:100]}..."
                        break
                        
            response += f"🔸 **{tag}**: {value}\n"
            response += f"   ⏰ {ts}\n"
            if sensor_info:
                response += f"   ℹ️ {sensor_info}\n"
            response += "\n"
            
        # 관련 지식 추가
        if context["relevant_knowledge"]:
            response += "\n💡 **관련 정보**:\n"
            for knowledge in context["relevant_knowledge"][:2]:
                response += f"• {knowledge['content'][:150]}...\n"
                
        return response
        
    def _format_alert_response(self, context: Dict[str, Any]) -> str:
        """경고 상태 응답 포맷"""  
        
        # QC 규칙과 현재 데이터 비교
        alerts = []
        
        for data in context["current_data"]:
            tag = data.get('tag_name')
            value = data.get('value')
            
            if not tag or value is None:
                continue
                
            # QC 규칙 찾기
            for rule in context["qc_rules"]:
                if rule.get('tag_name') == tag:
                    try:
                        val = float(value)
                        min_val = rule.get('min_val')
                        max_val = rule.get('max_val')
                        
                        if min_val and val < float(min_val):
                            alerts.append(f"🚨 {tag}: {value} (최소값 {min_val} 미만)")
                        elif max_val and val > float(max_val):
                            alerts.append(f"🚨 {tag}: {value} (최대값 {max_val} 초과)")
                            
                    except (ValueError, TypeError):
                        continue
                        
        if alerts:
            response = "⚠️ **경고 상태 감지**:\n\n"
            for alert in alerts[:5]:
                response += f"{alert}\n"
                
            # 관련 트러블슈팅 지식 추가
            troubleshooting = [k for k in context["relevant_knowledge"] 
                             if k.get('content_type') == 'troubleshooting']
            if troubleshooting:
                response += "\n🔧 **권장 조치**:\n"
                for item in troubleshooting[:2]:
                    response += f"• {item['content']}\n"
                    
            return response
        else:
            return "✅ 현재 모든 센서가 정상 범위 내에 있습니다."
            
    def _format_help_response(self) -> str:
        """도움말 응답"""
        return """
🤖 **AI 센서 어시스턴트 사용법**

다음과 같은 질문을 해보세요:

📊 **상태 조회**:
• "D101 센서 현재 상태는?"
• "전체 센서 상태 알려줘"

⚠️ **문제 진단**: 
• "경고 상태인 센서 있어?"
• "D100 온도가 높은 이유가 뭐야?"

📈 **분석 요청**:
• "어제와 비교해서 어떤 센서가 변했어?"
• "D101과 D102 상관관계 분석해줘"

🔧 **유지보수**:
• "정기 점검 일정 알려줘" 
• "센서 교체 후 주의사항은?"

자연어로 편하게 질문하세요! 🚀
        """
        
    async def _generate_contextual_response(self, query: str, context: Dict[str, Any]) -> str:
        """OpenAI 기반 지능형 응답 생성"""
        
        # OpenAI 클라이언트가 있으면 실제 LLM 사용
        if self.openai_client:
            return await self._generate_openai_response(query, context)
        
        # Fallback: 규칙 기반 응답
        return await self._generate_template_response(query, context)
    
    async def _generate_openai_response(self, query: str, context: Dict[str, Any]) -> str:
        """OpenAI GPT를 사용한 실제 AI 응답 생성"""
        
        # 컨텍스트 검증 및 로깅
        has_data = bool(context.get("current_data"))
        has_qc = bool(context.get("qc_rules"))
        has_knowledge = bool(context.get("relevant_knowledge"))
        
        print(f"🔍 RAG 컨텍스트 상태:")
        print(f"   - sensor_tags: {len(context.get('sensor_tags', []))}개")
        print(f"   - current_data: {len(context.get('current_data', []))}개")
        print(f"   - qc_rules: {len(context.get('qc_rules', []))}개")
        print(f"   - relevant_knowledge: {len(context.get('relevant_knowledge', []))}개")
        
        # 데이터가 전혀 없으면 안전한 응답 반환
        if not has_data and not has_qc and not has_knowledge:
            print("⚠️ RAG 컨텍스트 비어있음 - 데이터 없음 응답")
            return ("죄송합니다. 현재 데이터베이스 연결에 문제가 있거나 관련 데이터를 찾을 수 없습니다.\n\n"
                   "다음을 확인해주세요:\n"
                   "• 데이터베이스 연결 상태\n"
                   "• 센서명이 정확한지 (예: D100, D101)\n"
                   "• 실시간 데이터 수집이 정상 작동 중인지")
        
        try:
            # 프롬프트 구성 - 환각 방지 강화
            system_prompt = """당신은 산업용 센서 모니터링 시스템의 전문 AI 어시스턴트입니다.

중요 규칙:
1. 제공된 컨텍스트에 있는 정보만 사용하세요
2. 컨텍스트에 없는 수치, 임계값, 품질점수를 절대 생성하지 마세요
3. 확실하지 않은 정보는 "데이터 없음" 또는 "확인 불가"로 응답하세요
4. 숫자는 반드시 컨텍스트에서 제공된 값 그대로 사용하세요

응답 지침:
- 한국어로 명확하게 답변
- 정확한 데이터 기반 답변
- 추측이나 가정 금지
- 이모지는 구조화를 위해서만 사용"""

            # 컨텍스트 정보 구성
            context_info = []
            
            if context.get("current_data"):
                context_info.append("=== 현재 센서 데이터 ===")
                for data in context["current_data"][:5]:
                    context_info.append(f"- {data.get('tag_name', 'Unknown')}: {data.get('value', 'N/A')} (업데이트: {data.get('ts', 'N/A')})")
            
            if context.get("relevant_knowledge"):
                context_info.append("\n=== 관련 전문 지식 ===")
                for knowledge in context["relevant_knowledge"][:3]:
                    context_info.append(f"- [{knowledge.get('content_type', 'info')}] {knowledge.get('content', '')[:200]}...")
            
            if context.get("qc_violations"):
                context_info.append("\n=== QC 위반 사항 ===")
                for violation in context["qc_violations"][:3]:
                    context_info.append(f"- {violation}")
            
            user_prompt = f"""질문: {query}

컨텍스트 정보:
{chr(10).join(context_info) if context_info else '현재 이용 가능한 컨텍스트 정보가 없습니다.'}

위 정보를 바탕으로 사용자의 질문에 대해 정확하고 유용한 답변을 제공해주세요."""

            # OpenAI API 호출 - temperature 낮춤 (환각 방지)
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.2  # 0.7 → 0.2로 낮춤 (환각 감소)
            )
            
            ai_response = response.choices[0].message.content
            
            # 할루시네이션 방지 검증
            if self.hallucination_prevention:
                # 참조한 지식 베이스 ID 추출
                kb_ids = [k.get('id') for k in context.get('relevant_knowledge', []) if k.get('id')]
                
                # 응답 검증
                validation_result = await self.hallucination_prevention.validate_response(
                    ai_response, 
                    context,
                    kb_ids
                )
                
                # 신뢰도가 낮으면 경고 추가
                if validation_result.confidence < 0.7:
                    ai_response = await self.hallucination_prevention.enhance_response_with_disclaimer(
                        ai_response,
                        validation_result
                    )
                    
                    # 로그 기록
                    print(f"⚠️ 할루시네이션 검증 - 신뢰도: {validation_result.confidence:.2f}")
                    if validation_result.issues:
                        print(f"   이슈: {', '.join(validation_result.issues)}")
            
            return ai_response
            
        except Exception as e:
            print(f"OpenAI 응답 생성 실패: {e}")
            return await self._generate_template_response(query, context)
    
    async def _generate_template_response(self, query: str, context: Dict[str, Any]) -> str:
        """템플릿 기반 Fallback 응답"""
        
        # 지식 기반 응답 생성
        if context.get("relevant_knowledge"):
            response = "🧠 **관련 정보를 바탕으로 답변드립니다**:\n\n"
            
            for knowledge in context["relevant_knowledge"][:3]:
                content = knowledge['content']
                content_type = knowledge.get('content_type', '')
                similarity = knowledge.get('similarity_score', 0)
                
                type_emoji = {
                    'sensor_spec': '📊',
                    'troubleshooting': '🔧', 
                    'maintenance': '⚙️',
                    'operational_pattern': '📈',
                    'correlation': '🔗'
                }.get(content_type, '💡')
                
                response += f"{type_emoji} **{content_type.title()}** (관련도: {similarity:.1%})\n"
                response += f"{content}\n\n"
                
            # 현재 데이터도 포함
            if context.get("current_data"):
                response += "📊 **현재 데이터 참고**:\n"
                for data in context["current_data"][:3]:
                    tag = data.get('tag_name', '')
                    value = data.get('value', '')
                    response += f"• {tag}: {value}\n"
                    
            return response
            
        else:
            return "죄송합니다. 해당 질문에 대한 관련 정보를 찾을 수 없습니다. 다른 질문을 시도해보세요."


# 전역 RAG 엔진 인스턴스
rag_engine = RAGEngine()


async def initialize_rag_engine():
    """RAG 엔진 초기화"""
    await rag_engine.initialize()


async def get_rag_response(query: str, context: str | None = None) -> str:
    """RAG 기반 응답 생성.

    Args:
        query: 사용자 질문
        context: ai_state._prepare_context() 가 만든 보조 컨텍스트(센서/시스템 요약) 문자열.
                 선택적. RAGEngine.generate_response 가 build_context() 로 자체 컨텍스트
                 (sensor_tags/current_data/qc_rules/relevant_knowledge)를 구성하므로 필수는
                 query 뿐. 호출부(ai_state.py:133)와의 시그니처 호환을 위해 받는다.
                 NOTE: context 를 LLM 프롬프트에 직접 주입하는 것은 AI 품질개선 후속 작업.
    """
    # lazy-init: 첫 호출 시 1회 초기화 (openai_client/hallucination_prevention 세팅).
    # 이전엔 initialize() 가 라이브 경로에서 한 번도 호출되지 않아 항상 템플릿 응답이었음(audit C2).
    if not rag_engine._initialized:
        try:
            await rag_engine.initialize()
        except Exception as e:
            from reflex.utils import console
            console.warn(f"RAG init 실패(템플릿 모드로 계속): {e}")
    return await rag_engine.generate_response(query)