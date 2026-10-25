"""
실행 추적 데코레이터 - 실제로 호출되는 메서드와 파일 추적
"""
import functools
import inspect
import time
from pathlib import Path
from typing import Callable, Any
import os
from datetime import datetime

# 실행 추적 로그 파일
TRACE_LOG_DIR = Path("/tmp/edgeex_logs/execution_trace")
TRACE_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 세션 ID (프로세스 시작 시간 기준)
_SESSION_ID = datetime.now().strftime('%Y%m%d_%H%M%S')
TRACE_LOG_FILE = TRACE_LOG_DIR / f"execution_trace_{_SESSION_ID}.log"
TRACE_SUMMARY_FILE = TRACE_LOG_DIR / f"execution_summary_{_SESSION_ID}.txt"

# 호출된 함수/메서드 추적
_called_functions = set()
_called_files = set()
_call_counts = {}


def trace_execution(func: Callable) -> Callable:
    """
    함수/메서드 실행을 추적하는 데코레이터

    사용법:
        from edgeex_app.utils.execution_tracer import trace_execution

        @trace_execution
        def my_function():
            pass

        class MyClass:
            @trace_execution
            def my_method(self):
                pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 함수 정보 수집
        module = inspect.getmodule(func)
        module_name = module.__name__ if module else "unknown"

        # 파일 경로
        try:
            file_path = inspect.getfile(func)
            # edgeex_app 기준 상대 경로로 변환
            if "edgeex_app" in file_path:
                rel_path = file_path.split("edgeex_app")[-1].lstrip(os.sep).replace(os.sep, '.')
                rel_path = rel_path.replace('.py', '')
            else:
                rel_path = file_path
        except:
            rel_path = "unknown"

        # 함수 전체 이름 (모듈.클래스.함수)
        if hasattr(func, '__qualname__'):
            full_name = f"{module_name}.{func.__qualname__}"
        else:
            full_name = f"{module_name}.{func.__name__}"

        # 추적 기록
        _called_functions.add(full_name)
        _called_files.add(rel_path)
        _call_counts[full_name] = _call_counts.get(full_name, 0) + 1

        # 로그 기록
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        # 클래스 메서드인 경우 self/cls 제외
        if args and hasattr(args[0].__class__, func.__name__):
            arg_repr = f"args={args[1:]}, kwargs={kwargs}"
        else:
            arg_repr = f"args={args}, kwargs={kwargs}"

        log_entry = f"[{timestamp}] {full_name} | File: {rel_path} | Count: {_call_counts[full_name]}\n"

        # 파일에 기록 (append mode)
        with open(TRACE_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)

        # 실제 함수 실행
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.time() - start_time
            if elapsed > 0.1:  # 100ms 이상 걸린 함수만 기록
                slow_log = f"[{timestamp}] ⚠️  SLOW: {full_name} took {elapsed:.3f}s\n"
                with open(TRACE_LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(slow_log)

    return wrapper


def save_execution_summary():
    """
    실행 요약 정보 저장
    프로그램 종료 시 호출
    """
    with open(TRACE_SUMMARY_FILE, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("실행 추적 요약\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"세션 ID: {_SESSION_ID}\n")
        f.write(f"총 호출된 함수: {len(_called_functions)}개\n")
        f.write(f"총 사용된 파일: {len(_called_files)}개\n\n")

        f.write("=" * 80 + "\n")
        f.write("📁 사용된 파일 목록\n")
        f.write("=" * 80 + "\n\n")

        for file_path in sorted(_called_files):
            f.write(f"✅ {file_path}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("📊 함수 호출 빈도 (Top 50)\n")
        f.write("=" * 80 + "\n\n")

        # 호출 빈도순 정렬
        sorted_calls = sorted(_call_counts.items(), key=lambda x: x[1], reverse=True)

        for func_name, count in sorted_calls[:50]:
            f.write(f"{count:6d}x  {func_name}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write(f"상세 로그: {TRACE_LOG_FILE}\n")
        f.write("=" * 80 + "\n")

    print(f"📊 실행 추적 요약 저장됨: {TRACE_SUMMARY_FILE}")
    print(f"📝 상세 로그: {TRACE_LOG_FILE}")
    print(f"✅ {len(_called_functions)}개 함수, {len(_called_files)}개 파일 사용됨")


# atexit 등록 - 프로그램 종료 시 요약 저장
import atexit
atexit.register(save_execution_summary)


def get_execution_stats():
    """현재 실행 통계 반환 (런타임 중 확인용)"""
    return {
        "called_functions": len(_called_functions),
        "called_files": len(_called_files),
        "total_calls": sum(_call_counts.values()),
        "files": sorted(_called_files),
        "top_functions": sorted(_call_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    }
