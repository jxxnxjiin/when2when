from datetime import datetime, timedelta
from typing import Generator
from collections import defaultdict
from schemas import NormalizedData


# =============================================================================
# 기본 함수
# =============================================================================

def find_available_times(data: NormalizedData, participants: list[str]) -> Generator[datetime, None, None]:
    """
    특정 참가자들이 모두 가능한 시간대를 찾습니다.
    """
    participant_set = set(participants)
    for slot in data["slots"]:
        available_people = set(data["availability"].get(slot, []))
        if participant_set.issubset(available_people):
            yield slot


# =============================================================================
# 1. 연속된 시간대 묶기
# =============================================================================

def merge_consecutive_slots(
    slots: list[datetime], 
    slot_minutes: int = 15,
    min_duration_minutes: int = 0
) -> list[tuple[datetime, datetime]]:
    """
    연속된 시간 슬롯들을 묶어서 (시작, 종료) 튜플 리스트로 반환합니다.
    
    Args:
        slots: datetime 리스트 (정렬되어 있어야 함)
        slot_minutes: 슬롯 간격 (분)
        min_duration_minutes: 최소 연속 시간 (분). 이보다 짧은 범위는 제외
    
    Returns:
        [(시작시간, 종료시간), ...] 형태의 리스트
    """
    if not slots:
        return []
    
    sorted_slots = sorted(slots)
    merged = []
    
    start = sorted_slots[0]
    end = sorted_slots[0]
    
    for slot in sorted_slots[1:]:
        # 이전 슬롯과 연속인지 확인
        if slot - end == timedelta(minutes=slot_minutes):
            end = slot
        else:
            # 연속이 아니면 현재 범위 저장하고 새로 시작
            merged.append((start, end + timedelta(minutes=slot_minutes)))
            start = slot
            end = slot
    
    # 마지막 범위 추가
    merged.append((start, end + timedelta(minutes=slot_minutes)))
    
    # 최소 시간 필터링
    if min_duration_minutes > 0:
        min_duration = timedelta(minutes=min_duration_minutes)
        merged = [(s, e) for s, e in merged if (e - s) >= min_duration]
    
    return merged


def format_time_range(start: datetime, end: datetime) -> str:
    """시간 범위를 보기 좋게 포맷팅합니다."""
    duration = end - start
    hours, remainder = divmod(duration.seconds, 3600)
    minutes = remainder // 60
    
    duration_str = ""
    if hours > 0:
        duration_str += f"{hours}시간"
    if minutes > 0:
        duration_str += f" {minutes}분" if hours > 0 else f"{minutes}분"
    
    return f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')} ({duration_str.strip()})"


# =============================================================================
# 2. 날짜별 그룹핑
# =============================================================================

def group_by_date(
    time_ranges: list[tuple[datetime, datetime]]
) -> dict[str, list[tuple[datetime, datetime]]]:
    """
    시간 범위들을 날짜별로 그룹핑합니다.
    
    Returns:
        {"2025-01-05": [(시작, 종료), ...], ...}
    """
    grouped = defaultdict(list)
    
    for start, end in time_ranges:
        date_str = start.strftime("%Y-%m-%d")
        grouped[date_str].append((start, end))
    
    # 날짜순 정렬
    return dict(sorted(grouped.items()))


def get_available_times_grouped(
    data: NormalizedData, 
    participants: list[str],
    min_duration_minutes: int = 60
) -> dict[str, list[str]]:
    """
    참가자들이 모두 가능한 시간을 날짜별로 그룹핑하여 반환합니다.
    
    Args:
        data: NormalizedData
        participants: 참가자 이름 리스트
        min_duration_minutes: 최소 연속 시간 (분). 기본값 60분 (1시간)
    
    Returns:
        {"2025-01-05": ["14:00 ~ 16:30 (2시간 30분)", ...], ...}
    """
    slots = list(find_available_times(data, participants))
    merged = merge_consecutive_slots(slots, data["slot_minutes"], min_duration_minutes)
    grouped = group_by_date(merged)
    
    result = {}
    for date_str, ranges in grouped.items():
        result[date_str] = [format_time_range(s, e) for s, e in ranges]
    
    return result


# =============================================================================
# 4. 대안 제시
# =============================================================================

def find_alternatives(
    data: NormalizedData, 
    participants: list[str],
    max_missing: int = 1
) -> dict[str, dict[str, list[str]]]:
    """
    전원이 안 될 때, N-1명 (또는 N-max_missing명) 가능한 시간을 찾습니다.
    
    Args:
        data: NormalizedData
        participants: 원하는 참가자 리스트
        max_missing: 최대 빠질 수 있는 인원 수
    
    Returns:
        {
            "빠지는 사람 이름": {
                "2025-01-05": ["14:00 ~ 16:30", ...],
                ...
            },
            ...
        }
    """
    alternatives = {}
    
    for i in range(1, min(max_missing + 1, len(participants))):
        # i명이 빠지는 경우
        from itertools import combinations
        
        for missing in combinations(participants, i):
            remaining = [p for p in participants if p not in missing]
            grouped = get_available_times_grouped(data, remaining)
            
            if grouped:  # 가능한 시간이 있는 경우만
                missing_key = ", ".join(missing) + " 제외"
                alternatives[missing_key] = grouped
    
    return alternatives


def find_who_blocks(
    data: NormalizedData,
    participants: list[str]
) -> dict[str, int]:
    """
    누가 가장 많은 시간대를 막고 있는지 분석합니다.
    
    Returns:
        {"이름": 해당 인원 제외시 추가되는 슬롯 수, ...} (내림차순 정렬)
    """
    base_slots = set(find_available_times(data, participants))
    blockers = {}
    
    for person in participants:
        remaining = [p for p in participants if p != person]
        new_slots = set(find_available_times(data, remaining))
        added_slots = len(new_slots - base_slots)
        
        if added_slots > 0:
            blockers[person] = added_slots
    
    # 내림차순 정렬
    return dict(sorted(blockers.items(), key=lambda x: -x[1]))