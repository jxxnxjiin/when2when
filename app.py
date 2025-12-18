import streamlit as st
from get_data.when2meet import get_when2meet_data
from get_data.timepick import get_timepick_data
from analyze import (
    get_available_times_grouped,
    find_alternatives,
    find_who_blocks,
)

st.set_page_config(page_title="합주 시간 찾기", page_icon="🎵", layout="wide")


# =============================================================================
# 텍스트 출력 생성 함수
# =============================================================================
def generate_text_output(saved_songs: list, event_name: str) -> str:
    """저장된 곡 목록을 보기 좋은 텍스트로 변환합니다."""
    lines = []
    lines.append(f"🎵 {event_name} 합주 시간표")
    lines.append("=" * 40)
    lines.append("")
    
    for song in saved_songs:
        lines.append(f"## {song['song_name']}")
        lines.append(f"참여: {', '.join(song['participants'])}")
        lines.append("")
        
        for date, times in song['result'].items():
            lines.append(f"📅 {date}")
            for t in times:
                lines.append(f"   {t}")
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# 캐싱된 데이터 로드 함수 (같은 URL은 캐시 사용)
# =============================================================================
@st.cache_data(show_spinner=False, ttl=3600)  # 1시간 캐시
def load_when2meet(url: str):
    return get_when2meet_data(url)

@st.cache_data(show_spinner=False, ttl=3600)
def load_timepick(url: str):
    return get_timepick_data(url)


st.title("🎵 합주 시간 찾기")

# =============================================================================
# URL 자동 감지 함수
# =============================================================================
def detect_source(url: str) -> str | None:
    """URL에서 플랫폼을 자동 감지합니다."""
    if not url:
        return None
    if "when2meet.com" in url:
        return "when2meet"
    if "timepick.net" in url:
        return "timepick"
    return None

# =============================================================================
# 상단: URL 입력
# =============================================================================
col1, col2 = st.columns([4, 1])
with col1:
    url = st.text_input(
        "🔗 일정 링크",
        placeholder="when2meet 또는 timepick 링크를 붙여넣으세요",
        label_visibility="collapsed",
    )
with col2:
    load_button = st.button("불러오기", type="primary", use_container_width=True)

# =============================================================================
# 데이터 로드 및 저장된 곡 초기화
# =============================================================================
if "data" not in st.session_state:
    st.session_state.data = None

if "saved_songs" not in st.session_state:
    st.session_state.saved_songs = []

if "form_key" not in st.session_state:
    st.session_state.form_key = 0

if load_button and url:
    source = detect_source(url)
    if source is None:
        st.error("❌ 올바른 when2meet 또는 timepick 링크를 입력해주세요!")
    else:
        with st.spinner("데이터 불러오는 중... (첫 로드는 30초 이상 걸릴 수 있어요 ㅠ.ㅠ)"):
            try:
                if source == "when2meet":
                    st.session_state.data = load_when2meet(url)
                else:
                    st.session_state.data = load_timepick(url)
                st.success(f"✅ '{st.session_state.data['name']}' 로드 완료!")
            except Exception as e:
                st.error(f"❌ 오류: {e}")

# =============================================================================
# 메인 UI
# =============================================================================
if st.session_state.data:
    data = st.session_state.data
    
    st.divider()
    
    # 사용법 안내
    st.info("""
    **사용법** 💡  

    1️⃣ 곡명 입력 → 2️⃣ 참여 인원 선택 → 3️⃣ 결과 저장

    누적 저장 됩니다

    전체 결과 텍스트로 복사 가능 ~~~ 🦧
    """)
    
    # 곡명 입력
    song_name = st.text_input("🎸 곡명", placeholder="예: 머큐리얼", key=f"song_name_{st.session_state.form_key}")
    
    # 참가자 선택
    selected = st.multiselect(
        "👥 참여 인원 선택",
        options=data["participants"],
        default=None,
        key=f"participants_{st.session_state.form_key}",
    )
    
    if selected:
        st.divider()
        
        result = get_available_times_grouped(data, selected)  # 기본값: 1시간 이상
        
        if result:
            # 전원 가능 시간 있음
            st.success(f"✅ {len(selected)}명 전원 가능한 시간대")
            
            for date, times in result.items():
                with st.expander(f"📅 {date}", expanded=True):
                    for t in times:
                        st.write(f"  🕐 {t}")
            
            # 저장 버튼
            st.divider()
            if st.button("💾 이 결과 저장", type="primary"):
                # 이미 같은 곡이 있는지 확인
                existing = [s for s in st.session_state.saved_songs if s["song_name"] == song_name]
                if existing:
                    st.warning(f"'{song_name}' 곡이 이미 저장되어 있습니다. 삭제 후 다시 저장해주세요.")
                elif not song_name.strip():
                    st.warning("곡명을 입력해주세요!")
                else:
                    st.session_state.saved_songs.append({
                        "song_name": song_name,
                        "participants": selected.copy(),
                        "result": result.copy()
                    })
                    st.session_state.form_key += 1  # 폼 초기화
                    st.success(f"✅ '{song_name}' 저장 완료!")
                    st.rerun()
        else:
            # 전원 가능 시간 없음 → 대안 제시
            st.warning("😢 전원 가능한 시간이 없습니다!")
            
            st.subheader("🚫 안 되는 사람")
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
    
    # =========================================================================
    # 저장된 곡 목록
    # =========================================================================
    if st.session_state.saved_songs:
        st.divider()
        st.subheader("📋 Setlist")
        
        for i, song in enumerate(st.session_state.saved_songs):
            with st.expander(f"🎵 {song['song_name']} ({len(song['participants'])}명)", expanded=False):
                st.write(f"**참여자:** {', '.join(song['participants'])}")
                for date, times in song['result'].items():
                    st.write(f"📅 **{date}**")
                    for t in times:
                        st.write(f"  🕐 {t}")
                
                # 삭제 버튼
                if st.button(f"🗑️ 삭제", key=f"delete_{i}"):
                    st.session_state.saved_songs.pop(i)
                    st.rerun()
        
        st.divider()
        
        # 텍스트로 복사 버튼
        if st.button("📝 전체 결과 텍스트로 보기", use_container_width=True):
            text_output = generate_text_output(st.session_state.saved_songs, data["name"])
            st.code(text_output, language=None)

else:
    st.info("when2meet 또는 timepick 링크를 붙여넣고 불러오기를 눌러주세요~")

