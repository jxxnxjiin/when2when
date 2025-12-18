"""
When2meet 데이터 추출 모듈

"""

import requests
import re
from datetime import datetime
from schemas import NormalizedData


def _get_html(url: str) -> str:
    """When2meet 페이지의 HTML을 가져옵니다."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text


def _parse_people(html: str) -> dict[int, str]:
    """
    참가자 정보를 추출합니다.
    Returns: {id: name} 형태의 딕셔너리
    """
    pattern = r"PeopleNames\[(\d+)\]\s*=\s*'([^']+)';\s*PeopleIDs\[\1\]\s*=\s*(\d+);"
    matches = re.findall(pattern, html)
    
    people = {}
    for _, name, pid in matches:
        people[int(pid)] = name
    
    return people


def _parse_time_slots(html: str) -> dict[int, int]:
    """
    타임슬롯 정보를 추출합니다.
    Returns: {slot_index: unix_timestamp} 형태의 딕셔너리
    """
    pattern = r"TimeOfSlot\[(\d+)\]=(\d+);"
    matches = re.findall(pattern, html)
    
    time_slots = {}
    for idx, timestamp in matches:
        time_slots[int(idx)] = int(timestamp)
    
    return time_slots


def _parse_availability(html: str) -> dict[int, list[int]]:
    """
    가용성 정보를 추출합니다.
    Returns: {slot_index: [person_id, ...]} 형태의 딕셔너리
    """
    pattern = r"AvailableAtSlot\[(\d+)\]\.push\((\d+)\);"
    matches = re.findall(pattern, html)
    
    availability = {}
    for slot_idx, person_id in matches:
        slot_idx = int(slot_idx)
        person_id = int(person_id)
        
        if slot_idx not in availability:
            availability[slot_idx] = []
        availability[slot_idx].append(person_id)
    
    return availability


def _parse_event_name(html: str) -> str:
    """이벤트 이름을 추출합니다."""
    pattern = r"<title>(.+?)\s*-\s*When2meet</title>"
    match = re.search(pattern, html)
    return match.group(1) if match else "Unknown Event"


def get_when2meet_data(url: str) -> NormalizedData:
    """
    When2meet URL에서 데이터를 추출하고 정규화된 형태로 반환합니다.
    
    Args:
        url: When2meet 이벤트 URL
    
    Returns:
        NormalizedData: 정규화된 데이터 딕셔너리
    """
    html = _get_html(url)
    
    # 데이터 파싱
    people = _parse_people(html)  # {id: name}
    time_slots = _parse_time_slots(html)  # {slot_idx: timestamp}
    raw_availability = _parse_availability(html)  # {slot_idx: [person_ids]}
    event_name = _parse_event_name(html)
    
    # 정규화: slot_idx → datetime, person_id → name
    availability: dict[datetime, list[str]] = {}
    slots: list[datetime] = []
    
    for slot_idx, timestamp in sorted(time_slots.items(), key=lambda x: x[1]):
        dt = datetime.fromtimestamp(timestamp)
        slots.append(dt)
        
        # 해당 슬롯에 가능한 사람들
        if slot_idx in raw_availability:
            person_ids = raw_availability[slot_idx]
            names = [people[pid] for pid in person_ids if pid in people]
            availability[dt] = names
        else:
            availability[dt] = []
    
    # 참가자 목록 (이름 기준 정렬)
    participants = sorted(people.values())
    
    return {
        'source': 'when2meet',
        'name': event_name,
        'participants': participants,
        'slot_minutes': 15, 
        'slots': slots,
        'availability': availability,
    }