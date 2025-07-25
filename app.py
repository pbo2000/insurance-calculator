# app.py

import streamlit as st
import pandas as pd

# --- 상수 정의 ---
TERMS = (5, 7, 10, 20)
TERM_LABELS = ("5년", "7년", "10년", "20년")
TAX_RATE = 0.154  # 세율 15.4%
DEFER_RATE = 0.02 # 거치 이율 2%

# --- Streamlit 페이지 설정 ---
st.set_page_config(page_title="종신보험 계산기", page_icon="🏦", layout="wide")

# --- CSS를 이용해 사이드바 너비 조정 ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        width: 320px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- 앱 제목 ---
st.title("종신보험 은행 단리 환산 계산기 📈")
st.write("월 보험료와 환급률을 입력하여 납입 기간별 실제 이자율을 확인해보세요.")

# --- 입력 UI (사이드바에 배치하여 화면을 깔끔하게 구성) ---
with st.sidebar:
    st.header("⚙️ 입력 항목")
    
    # st.number_input은 숫자 입력 완료 시 자동으로 천 단위 콤마를 표시해줍니다.
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
    # st.columns를 사용해 체크박스를 가로로 정렬
    selected_periods = {}
    cols = st.columns(len(TERM_LABELS))
    for i, label in enumerate(TERM_LABELS):
        # value=False로 변경하여 처음에는 체크가 해제된 상태로 시작
        selected_periods[TERMS[i]] = cols[i].checkbox(label, value=False) 

# --- 계산 버튼 및 결과 표시 ---
if st.button("계산 실행하기", type="primary", use_container_width=True):
    rate = rate_pct / 100.0
    
    results_data = [] # 결과를 저장할 리스트
    bank_rates = {}   # 환산 금리 결과를 저장할 딕셔너리

    # 선택된 기간에 대해서만 계산 수행
    for years, is_selected in selected_periods.items():
        if not is_selected:
            continue

        months = years * 12
        principal_sum = premium * months
        insurance_total = principal_sum * rate
        interest_ins = insurance_total - principal_sum

        # 표에 들어갈 데이터 추가
        results_data.append({
            "납입 기간": f"{years}년 ({months}개월)",
            "총 납입 원금": principal_sum,
            "10년 시점 순수 이자": interest_ins,
            "10년 시점 총 환급액": insurance_total
        })

        # 은행 단리 환산 금리 계산 로직 (기존 코드와 동일)
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
        
        # 결과를 Pandas DataFrame으로 변환하여 st.dataframe으로 보기 좋게 표시
        df = pd.DataFrame(results_data)
        st.dataframe(
            df.style.format({
                "총 납입 원금": "{:,.0f}원",
                "10년 시점 순수 이자": "{:,.0f}원",
                "10년 시점 총 환급액": "{:,.0f}원"
            }),
            use_container_width=True, # 너비를 꽉 채움
            hide_index=True
        )

        st.header("🏦 은행 단리 환산 금리 (세후)")
        
        # st.columns로 결과를 나란히 표시
        # len(bank_rates)가 0인 경우 에러가 발생할 수 있으므로, 1 이상일 때만 실행
        if len(bank_rates) > 0:
            rate_cols = st.columns(len(bank_rates))
            
            for i, (years, data) in enumerate(bank_rates.items()):
                with rate_cols[i]:
                    # st.metric으로 핵심 지표를 강조
                    st.metric(
                        label=f"**{years}년 납입 시**", 
                        value=f"{data['rate']:.2f}%"
                    )
                    st.info(f"10년 거치 이자 효과: {data['defer_interest']:,.0f}원")
