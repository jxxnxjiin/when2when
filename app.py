import streamlit as st
from get_data.when2meet import get_when2meet_data
from get_data.timepick import get_timepick_data
from analyze import (
    get_available_times_grouped,
    find_alternatives,
    find_who_blocks,
)

st.set_page_config(page_title="합주 시간 찾기", page_icon="🎵", layout="wide")

st.title("🎵 합주 시간 찾기")

# =============================================================================
# 사이드바: 데이터 소스 설정
# =============================================================================
with st.sidebar:
    st.header("📊 데이터 소스")
    
    source = st.selectbox(
        "플랫폼 선택",
        ["when2meet", "timepick"],
    )
    
    url = st.text_input(
        "URL 입력",
        placeholder="https://www.when2meet.com/?12345-abcde",
    )
    
    load_button = st.button("데이터 불러오기", type="primary", use_container_width=True)

# =============================================================================
# 데이터 로드
# =============================================================================
if "data" not in st.session_state:
    st.session_state.data = None

if load_button and url:
    with st.spinner("데이터 불러오는 중..."):
        try:
            if source == "when2meet":
                st.session_state.data = get_when2meet_data(url)
            else:
                st.session_state.data = get_timepick_data(url)
            st.success(f"✅ '{st.session_state.data['name']}' 로드 완료!")
        except Exception as e:
            st.error(f"❌ 오류: {e}")

# =============================================================================
# 메인 UI
# =============================================================================
if st.session_state.data:
    data = st.session_state.data
    
    st.divider()
    
    # 곡명 입력
    song_name = st.text_input("🎸 곡명", placeholder="예: 밤편지")
    
    # 참가자 선택
    selected = st.multiselect(
        "👥 참여 인원 선택",
        options=data["participants"],
        default=None,
    )
    
    if selected:
        st.divider()
        
        # 결과 계산
        result = get_available_times_grouped(data, selected)
        
        if result:
            # 전원 가능 시간 있음
            st.success(f"✅ {len(selected)}명 전원 가능한 시간대")
            
            for date, times in result.items():
                with st.expander(f"📅 {date}", expanded=True):
                    for t in times:
                        st.write(f"  🕐 {t}")
        else:
            # 전원 가능 시간 없음 → 대안 제시
            st.warning("😢 전원 가능한 시간이 없습니다!")
            
            # 누가 막고 있는지
            st.subheader("🚫 일정 조율 방해자")
            blockers = find_who_blocks(data, selected)
            
            if blockers:
                for name, count in blockers.items():
                    st.write(f"- **{name}**: 제외 시 +{count}개 슬롯 확보")
            else:
                st.write("분석 불가")
            
            # 대안 제시
            st.subheader("💡 대안 (1명 제외 시)")
            alternatives = find_alternatives(data, selected, max_missing=1)
            
            for missing_info, times in alternatives.items():
                with st.expander(f"📌 {missing_info}"):
                    for date, time_list in times.items():
                        st.write(f"**{date}**")
                        for t in time_list:
                            st.write(f"  🕐 {t}")

else:
    st.info("👈 사이드바에서 URL을 입력하고 데이터를 불러오세요!")

