from datetime import datetime
from typing import TypedDict, List, Dict

class NormalizedData(TypedDict):
    source: str                              # 'when2meet' | 'timepick'
    name: str                                # 이벤트 이름
    participants: List[str]                  # 전체 인원
    slot_minutes: int                        # 슬롯 간격 (분)
    slots: List[datetime]                    # 전체 시간대
    availability: Dict[datetime, List[str]]  # {시간: [가능한 사람들]}