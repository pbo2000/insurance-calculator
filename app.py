# app.py

import streamlit as st
import pandas as pd

# --- 상수 정의 ---
TERMS = (5, 7, 10, 20)
TERM_LABELS = ("5년", "7년", "10년", "20년")
TAX_RATE = 0.154  # 세율 15.4%
DEFER_RATE = 0.02 # 거치 이율 2%

# --- Streamlit 페이지 설정 ---
# layout="centered"는 모바일에서 콘텐츠가 중앙에 집중되도록 하여 가독성을 높입니다.
st.set_page_config(page_title="종신보험 계산기", page_icon="🏦", layout="centered")

# --- 앱 제목 ---
st.title("종신보험 환산 계산기 📈")
st.write("월 보험료와 환급률을 입력하여 기간별 실제 이자율을 확인해보세요.")
st.write("---")

# --- 입력 UI (사이드바 대신 메인 화면에 폼으로 구성) ---
# st.form을 사용하면 모든 입력을 마친 후 버튼을 눌렀을 때 한 번만 계산을 실행합니다.
with st.form("input_form"):
    st.subheader("⚙️ 입력 항목")
    
    # value=None과 placeholder를 사용하여 기본값을 비워둠
    # st.number_input은 입력 완료 후(포커스 아웃) 자동으로 천단위 콤마를 적용합니다.
    premium = st.number_input(
        "월 보험료 (원)", 
        min_value=0,
        value=None,  # 기본값 없음
        step=10000,
        placeholder="예: 100000",
        help="매월 납입할 보험료를 입력하세요."
    )
    
    rate_pct = st.number_input(
        "10년 시점 환급률 (%)", 
        min_value=0.0, 
        value=None,  # 기본값 없음
        step=0.1, 
        format="%.1f",
        placeholder="예: 110.5",
        help="보험설계서 상의 10년 시점 환급률을 입력하세요."
    )
    
    st.write("납입기간 선택 (중복 선택 가능)")
    # 모바일에서 가장 안정적인 세로 정렬을 위해 개별 체크박스로 변경
    selected_periods = {}
    selected_periods[TERMS[0]] = st.checkbox(TERM_LABELS[0], value=False)
    selected_periods[TERMS[1]] = st.checkbox(TERM_LABELS[1], value=False)
    selected_periods[TERMS[2]] = st.checkbox(TERM_LABELS[2], value=False)
    selected_periods[TERMS[3]] = st.checkbox(TERM_LABELS[3], value=False)
    
    st.write("") # 여백
    # 폼 제출 버튼
    submitted = st.form_submit_button("계산 실행하기", type="primary", use_container_width=True)

# --- 계산 버튼 클릭 후 결과 표시 ---
if submitted:
    # 입력값 유효성 검사
    if premium is None or rate_pct is None or premium <= 0 or rate_pct <= 0:
        st.error("월 보험료와 환급률을 0보다 큰 값으로 입력해주세요.")
    elif not any(selected_periods.values()):
        st.warning("계산할 납입기간을 하나 이상 선택해주세요.")
    else:
        rate = rate_pct / 100.0
        
        results_data = []
        bank_rates = {}

        for years, is_selected in selected_periods.items():
            if not is_selected:
                continue

            months = years * 12
            principal_sum = premium * months
            insurance_total = principal_sum * rate
            interest_ins = insurance_total - principal_sum

            results_data.append({
                "납입 기간": f"{years}년",
                "총 납입 원금": principal_sum,
                "순수 이자": interest_ins,
                "총 환급액": insurance_total
            })

            defer_years = max(0, 10 - years)
            defer_interest = principal_sum * DEFER_RATE * defer_years * (1 - TAX_RATE)
            denom = premium * (months * (months + 1) / 24) * (1 - TAX_RATE)
            net_target = interest_ins - defer_interest
            bank_r = net_target / denom if denom else 0
            bank_pct = bank_r * 100
            
            bank_rates[years] = {
                "rate": bank_pct,
                "defer_interest": defer_interest,
                "net_interest": net_target,
                "defer_years": defer_years
            }
        
        st.write("---")
        st.header("📊 계산 결과 요약")
        
        df = pd.DataFrame(results_data)
        df.rename(columns={
            "총 납입 원금": "원금", 
            "순수 이자": "이자", 
            "총 환급액": "환급액"
        }, inplace=True)
        
        # 표 스타일링: 중앙 정렬, 글자 크기 및 굵기 조절
        st.dataframe(
            df.style.format({
                "원금": "{:,.0f}원",
                "이자": "{:,.0f}원",
                "환급액": "{:,.0f}원"
            }).set_table_styles([{
                'selector': 'th, td',
                'props': [
                    ('text-align', 'center'),
                    ('font-size', '1.1rem'),
                    ('font-weight', 'bold')
                ]
            }]),
            use_container_width=True,
            hide_index=True
        )

        st.header("🏦 은행 단리 환산 금리 (세후)")
        
        if len(bank_rates) > 0:
            for years, data in sorted(bank_rates.items()):
                with st.expander(f"**{years}년 납입** 환산 금리 상세보기", expanded=True):
                    # 7년 납입일 경우 특별 로직 적용
                    if years == 7:
                        st.metric(
                            label=f"7년 적금 이자율 (세후)", 
                            value=f"{data['rate']:.2f}%"
                        )
                        st.info(f"7년 적금 이자: {data['net_interest']:,.0f}원")
                        st.info(f"3년 거치 이자 효과: {data['defer_interest']:,.0f}원")
                    else:
                        st.metric(
                            label=f"환산 금리 (세후)", 
                            value=f"{data['rate']:.2f}%"
                        )
                        # 거치 기간이 0년 초과일 때만 표시
                        if data['defer_years'] > 0:
                            st.info(f"{data['defer_years']}년 거치 이자 효과: {data['defer_interest']:,.0f}원")
