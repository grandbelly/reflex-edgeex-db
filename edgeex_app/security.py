"""
edgeEX Dashboard 보안 유틸리티
환경변수 검증, 로깅 보안, CSP 설정
"""
import os
import logging
from urllib.parse import urlparse
from typing import Optional


class SecurityValidator:
    """보안 검증 클래스"""

    @staticmethod
    def validate_environment_variables() -> bool:
        """환경변수 보안 검증"""
        dsn = os.getenv('TS_DSN')
        if not dsn:
            raise ValueError("TS_DSN 환경변수가 설정되지 않았습니다")

        # DSN 파싱 및 검증
        try:
            parsed = urlparse(dsn)
            if parsed.scheme not in ['postgresql', 'postgres']:
                raise ValueError(f"지원하지 않는 DB 스키마: {parsed.scheme}")

            if not parsed.hostname:
                raise ValueError("DB 호스트가 지정되지 않았습니다")

            if not parsed.username:
                raise ValueError("DB 사용자가 지정되지 않았습니다")

        except Exception as e:
            raise ValueError(f"잘못된 DSN 형식: {e}")

        # DB 보안 설정 검증
        app_env = os.getenv('APP_ENV', 'development')

        # 관리자 계정 사용 검증 (경고만 표시)
        dangerous_usernames = ['postgres', 'root', 'admin', 'administrator', 'sa']
        if parsed.username and parsed.username.lower() in dangerous_usernames:
            logging.warning(f"[SECURITY] 관리자 계정({parsed.username}) 사용 중 - 읽기전용 계정 사용 권장")

        # SSL 설정 검증 (경고만 표시)
        if 'sslmode=disable' in dsn.lower():
            logging.warning("[SECURITY] SSL이 비활성화됨 - SSL 사용 권장")

        # 기본 패스워드 패턴 검증 (경고만 표시)
        if parsed.password:
            weak_passwords = ['admin', 'password', '123456', 'postgres', 'root']
            if parsed.password.lower() in weak_passwords:
                logging.warning("[SECURITY] 약한 패스워드 사용 중 - 강력한 패스워드 사용 권장")

        # 로컬호스트 사용 검증 (엣지 로컬 통합 시험 환경을 위해 경고만 출력)
        if app_env == 'production':
            if 'localhost' in dsn or '127.0.0.1' in dsn:
                logging.warning("[SECURITY] 로컬호스트 DB(127.0.0.1/localhost) 연결 사용 중")

        return True

    @staticmethod
    def mask_sensitive_data(data: str) -> str:
        """민감한 데이터 마스킹"""
        if not data:
            return ""

        # 패스워드 마스킹 (postgresql://user:password@host:port/db)
        if '://' in data and '@' in data:
            try:
                parsed = urlparse(data)
                if parsed.password:
                    masked_password = '*' * len(parsed.password)
                    return data.replace(parsed.password, masked_password)
            except Exception:
                pass

        return data

    @staticmethod
    def setup_secure_logging():
        """보안 로깅 설정"""
        logging.getLogger("reflex").setLevel(logging.WARNING)
        logging.getLogger("granian").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

        app_logger = logging.getLogger("edgeex_app")
        app_logger.setLevel(logging.INFO)

        class SensitiveDataFilter(logging.Filter):
            def filter(self, record):
                if hasattr(record, 'msg') and isinstance(record.msg, str):
                    record.msg = SecurityValidator.mask_sensitive_data(record.msg)
                return True

        for handler in logging.getLogger().handlers:
            handler.addFilter(SensitiveDataFilter())


def get_csp_headers() -> dict:
    """Content Security Policy 헤더 생성"""
    app_env = os.getenv('APP_ENV', 'development')

    if app_env == 'production':
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' ws: wss:; "
            "img-src 'self' data:; "
            "font-src 'self'"
        )
        logging.info("[SECURITY] 운영환경: 강화된 CSP 적용 (unsafe-eval 비활성화)")
    else:
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' ws: wss:; "
            "img-src 'self' data:; "
            "font-src 'self'"
        )
        logging.warning("[SECURITY] 개발환경: CSP에서 unsafe-eval 허용 중")

    return {
        "Content-Security-Policy": csp_policy,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if app_env == 'production' else None
    }


def validate_startup_security():
    """애플리케이션 시작시 보안 검증"""
    try:
        SecurityValidator.validate_environment_variables()
        SecurityValidator.setup_secure_logging()

        app_env = os.getenv('APP_ENV', 'development')
        logging.info(f"보안 검증 완료 - 환경: {app_env}")

        if app_env == 'development':
            logging.info("개발환경 - 일부 보안 경고는 무시될 수 있습니다")

        return True

    except Exception as e:
        logging.error(f"보안 검증 실패: {e}")
        raise


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    try:
        validate_startup_security()
        print("보안 검증 성공")
    except Exception as e:
        print(f"보안 검증 실패: {e}")
