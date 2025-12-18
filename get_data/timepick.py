"""
Timepick 데이터 추출 모듈
"""

import requests
from datetime import datetime, timedelta
from schemas import NormalizedData


def _get_api_url(url: str) -> str:
    """Timepick 링크에서 API URL 추출"""
    schedule_id = url.strip("/").split("/")[-1]
    return f"https://backend.timepick.net/api/event/{schedule_id}/"


def _fetch_data(api_url: str) -> dict:
    """API에서 JSON 데이터 가져오기"""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()


def _parse_dates(dates_str: str) -> list[str]:
    """쉼표로 구분된 날짜 문자열을 리스트로 변환합니다."""
    return [d.strip() for d in dates_str.split(",")]


def _generate_slots(dates: list[str], start_hour: int, end_hour: int) -> list[datetime]:
    """
    날짜와 시간 범위로 모든 타임슬롯을 생성합니다. (15분 단위)
    
    Args:
        dates: ["2025-12-18", "2025-12-19", ...]
        start_hour: 시작 시간
        end_hour: 종료 시간
    """
    if end_hour == 0:
        end_hour = 24
    
    slots = []
    for date_str in dates:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        
        current_time = date.replace(hour=start_hour, minute=0)
        end_time = date.replace(hour=0, minute=0) + timedelta(hours=end_hour)
        
        while current_time < end_time:
            slots.append(current_time)
            current_time += timedelta(minutes=15)
    
    return slots


def _parse_availability(
    group_availability: dict[str, str],
    slots: list[datetime]
) -> dict[datetime, list[str]]:
    """
    availability 문자열을 정규화된 형태로 변환
    
    Args:
        group_availability: {"이름": "111100001111...", ...}
        slots: [datetime, datetime, ...]
    
    Returns:
        {datetime: ["가능한", "사람들"], ...}
    """
    availability: dict[datetime, list[str]] = {slot: [] for slot in slots}
    
    for name, avail_str in group_availability.items():
        for i, bit in enumerate(avail_str):
            if i < len(slots) and bit == "1":
                availability[slots[i]].append(name)
    
    return availability


def get_timepick_data(url: str) -> NormalizedData:
    """
    Timepick URL에서 데이터를 추출하고 정규화된 형태로 반환합니다.
    
    Args:
        url: Timepick 이벤트 URL 또는 API URL
    
    Returns:
        NormalizedData: 정규화된 데이터 딕셔너리
    """
    # URL 형식 처리
    if "backend.timepick.net" in url:
        api_url = url
    else:
        api_url = _get_api_url(url)
    
    raw_data = _fetch_data(api_url)
    
    dates = _parse_dates(raw_data["dates"])
    start_hour = raw_data["startTime"]
    end_hour = raw_data["endTime"]

    slots = _generate_slots(dates, start_hour, end_hour)
    availability = _parse_availability(
        raw_data["groupAvailability"],
        slots
    )
    
    return {
        "source": "timepick",
        "name": raw_data["name"],
        "participants": raw_data["participants"],
        "slot_minutes": 15,
        "slots": slots,
        "availability": availability,
    }