from get_data.timepick import get_timepick_data

if __name__ == "__main__":
    url = input("타임픽 링크를 입력하세요:\n")
    data = get_timepick_data(url) # 정규화 데이터