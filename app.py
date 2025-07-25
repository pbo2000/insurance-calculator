# app.py

import streamlit as st
import pandas as pd

# --- 상수 정의 ---
TERMS = (5, 7, 10, 20)
TERM_LABELS = ("5년", "7년", "10년", "20년")
TAX_RATE = 0.154  # 세율 15.4%
DEFER_RATE = 0.02 # 거치 이율 2%

# --- Streamlit 페이지 설정 ---
# layout="centered"로 변경하여 모바일에서 콘텐츠가 중앙에 집중되도록 합니다.
st.set_page_config(page_title="종신보험 계산기", page_icon="🏦", layout="centered")

# --- 앱 제목 ---
st.title("종신보험 환산 계산기 📈")
st.write("월 보험료와 환급률을 입력하여 기간별 실제 이자율을 확인해보세요.")

# --- 입력 UI (사이드바) ---
with st.sidebar:
    st.header("⚙️ 입력 항목")
    
    premium = st.number_input(
        "월 보험료 (원)", 
        min_value=10000, 
        value=100000, 
        step=10000,
        help="매월 납입할 보험료를 입력하세요."
    )
    
    rate_pct = st.number_input(
        "10년 시점 환급률 (%)", 
        min_value=0.0, 
        value=110.0, 
        step=0.1, 
        format="%.1f",
        help="보험설계서 상의 10년 시점 환급률을 입력하세요."
    )

    st.subheader("납입기간 선택")
    # 모바일에서 가장 안정적인 세로 정렬을 위해 개별 체크박스로 변경
    selected_periods = {}
    selected_periods[TERMS[0]] = st.checkbox(TERM_LABELS[0], value=False)
    selected_periods[TERMS[1]] = st.checkbox(TERM_LABELS[1], value=False)
    selected_periods[TERMS[2]] = st.checkbox(TERM_LABELS[2], value=False)
    selected_periods[TERMS[3]] = st.checkbox(TERM_LABELS[3], value=False)

# --- 계산 버튼 ---
if st.button("계산 실행하기", type="primary", use_container_width=True):
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
            "defer_interest": defer_interest
        }

    if not results_data:
        st.warning("계산할 납입기간을 하나 이상 선택해주세요.")
    else:
        st.header("📊 계산 결과 요약")
        
        df = pd.DataFrame(results_data)
        # 모바일에서는 가로 스크롤이 생길 수 있으므로, 컬럼명을 줄여서 표시
        df.rename(columns={
            "총 납입 원금": "원금", 
            "순수 이자": "이자", 
            "총 환급액": "환급액"
        }, inplace=True)
        
        st.dataframe(
            df.style.format({
                "원금": "{:,.0f}원",
                "이자": "{:,.0f}원",
                "환급액": "{:,.0f}원"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.header("🏦 은행 단리 환산 금리 (세후)")
        
        if len(bank_rates) > 0:
            for years, data in sorted(bank_rates.items()):
                with st.expander(f"**{years}년 납입** 환산 금리 상세보기", expanded=True):
                    st.metric(
                        label=f"환산 금리 (세후)", 
                        value=f"{data['rate']:.2f}%"
                    )
                    st.info(f"10년 거치 이자 효과: {data['defer_interest']:,.0f}원")
