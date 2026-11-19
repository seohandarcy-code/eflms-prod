"""한국 시간 기준 '오늘' (2026-11-19, Stage 21-1).

PDEP 컨테이너는 보통 UTC라 date.today()는 한국 시간 오전 9시 전까지 전날이다 — 새벽에 도는 점수 갱신이
하루 늦은 기준일로 계산되지 않도록, 계산 기준일의 기본값은 이 함수로 정한다. 한국은 서머타임이 없어
UTC+9 고정으로 충분하다(tzdata 같은 의존성 불필요).
"""
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9), "KST")


def now_kst() -> datetime:
    return datetime.now(KST)


def now_kst_naive() -> datetime:
    """DB에 저장하는 시각(타임존 없는 DateTime 컬럼) — 한국 시간 기준으로 기록한다(Stage 21-1c)."""
    return now_kst().replace(tzinfo=None)


def today_kst() -> date:
    return now_kst().date()
