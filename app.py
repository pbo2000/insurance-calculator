# app.py

import streamlit as st
import pandas as pd

# --- 상수 정의 ---
TERMS = (5, 7, 10, 20)
TERM_LABELS = ("5년", "7년", "10년", "20년")
TAX_RATE = 0.154  # 이자소득세율 15.4%
DEPOSIT_RATE = 0.02 # 거치 기간에 적용할 예금 금리 (연 2% 복리)

# --- Streamlit 페이지 설정 ---
# layout="centered"는 모바일에서 콘텐츠가 중앙에 집중되도록 하여 가독성을 높입니다.
st.set_page_config(page_title="종신보험 계산기", page_icon="🏦", layout="centered")

# --- 앱 제목 ---
st.title("종신보험 환산 계산기 📈")
st.write("월 보험료와 10년 시점 환급률을 입력하여, 은행 적금/예금 상품과 수익률을 비교해보세요.")
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
        placeholder="예: 131000",
        help="매월 납입할 보험료를 입력하세요."
    )
    
    rate_pct = st.number_input(
        "10년 시점 환급률 (%)", 
        min_value=0.0, 
        value=None,  # 기본값 없음
        step=0.1, 
        format="%.1f",
        placeholder="예: 119.1",
        help="보험설계서 상의 10년 시점 환급률을 입력하세요. 납입기간과 관계없이 10년째의 환급률입니다."
    )
    
    st.write("납입기간 선택 (중복 선택 가능)")
    # 모바일에서 가장 안정적인 세로 정렬을 위해 개별 체크박스로 변경
    selected_periods = {}
    selected_periods[TERMS[0]] = st.checkbox(f"{TERM_LABELS[0]} 납입 (+5년 거치)", value=False)
    selected_periods[TERMS[1]] = st.checkbox(f"{TERM_LABELS[1]} 납입 (+3년 거치)", value=True) # 7년납 기본 선택
    selected_periods[TERMS[2]] = st.checkbox(f"{TERM_LABELS[2]} 납입 (거치 없음)", value=False)
    selected_periods[TERMS[3]] = st.checkbox(f"{TERM_LABELS[3]} 납입 (거치 없음)", value=False)
    
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
        # 10년 시점의 총 환급액은 납입 기간과 관계없이 동일하다고 가정
        # (보험 상품이 보통 그렇게 설계됨)
        # 예: 7년납 10년 환급률 119.1% -> 총 납입원금(7년치) * 1.191
        
        results_data = []
        bank_rates = {}

        for years, is_selected in selected_periods.items():
            if not is_selected:
                continue

            months = years * 12
            principal_sum = premium * months
            
            # 10년 시점 환급액 계산.
            # 총 납입 원금(years 기준)에 10년 시점 환급률을 곱함
            insurance_total_at_10_years = principal_sum * (rate_pct / 100.0)
            
            # 보험의 순수 이자 (세후 개념, 보험 차익은 비과세이므로)
            interest_ins = insurance_total_at_10_years - principal_sum

            results_data.append({
                "납입 기간": f"{years}년",
                "총 납입 원금": principal_sum,
                "10년 후 순수 이자 (비과세)": interest_ins,
                "10년 후 총 환급액": insurance_total_at_10_years
            })

            # --- 은행 상품과 비교를 위한 환산 금리 계산 로직 (수정됨) ---
            # 1. 보험의 비과세 이자와 동일한 실 수령액을 얻기 위해 필요한 은행의 '세전' 이자를 역산.
            equivalent_pre_tax_interest = interest_ins / (1 - TAX_RATE) if (1 - TAX_RATE) > 0 else 0

            bank_r = 0
            description = ""

            # 2. 납입기간에 따라 다른 계산 모델 적용
            if years < 10:
                # [모델 A] 납입기간 < 10년: 'N년 적금 + (10-N)년 예금' 모델
                grace_years = 10 - years
                # (10-N)년간의 예금(복리)으로 불어나는 부분을 역산하기 위한 계수
                deposit_factor = (1 + DEPOSIT_RATE) ** grace_years
                
                # 총 세전 이자(equivalent_pre_tax_interest)는 
                # [적금 기간 이자 + 예금 거치 기간 이자]로 구성됨.
                # 전체 과정(10년) 후의 총 원리금(세전)을 계산
                total_pre_tax_value = principal_sum + equivalent_pre_tax_interest
                
                # 예금 거치 직전(납입 종료 시점)의 원리금(세전)을 역산
                value_before_deposit = total_pre_tax_value / deposit_factor
                
                # 적금 기간(N년) 동안 발생한 순수 이자(세전)를 계산
                interest_during_saving_period = value_before_deposit - principal_sum
                
                # 이 이자를 발생시키는 적금 금리(r)을 역산
                # 이자 = 월납입액 * n(n+1)/2 * (r/12) => r = 이자 * 12 / (월납입액 * n(n+1)/2)
                denom = premium * (months * (months + 1) / 24.0)
                bank_r = interest_during_saving_period / denom if denom > 0 else 0
                
                bank_pct = bank_r * 100
                description = (
                    f"이 보험 상품은 **{years}년 동안 연 {bank_pct:.2f}% 단리 적금**에 가입하고, "
                    f"만기된 원리금(세전)을 **{grace_years}년 동안 연 {DEPOSIT_RATE*100:.0f}% 복리 예금**에 "
                    "거치했을 때와 동일한 수익률입니다."
                )

            else: # years >= 10
                # [모델 B] 납입기간 >= 10년: 'N년 적금' 모델 (기존 로직과 동일)
                # 이 경우, 거치기간 없이 N년간의 적금 수익률만 계산
                denom = premium * (months * (months + 1) / 24.0)
                bank_r = equivalent_pre_tax_interest / denom if denom > 0 else 0
                
                bank_pct = bank_r * 100
                description = (
                    f"이 보험 상품의 수익률은 **연 {bank_pct:.2f}%짜리 {years}년 만기 일반과세 단리 적금**"
                    " 상품과 동일한 수익률입니다."
                )
            
            bank_rates[years] = { "rate": bank_r * 100, "description": description }
        
        st.write("---")
        st.header("📊 계산 결과 요약")
        
        df = pd.DataFrame(results_data)
        # 컬럼 이름 변경
        df.rename(columns={
            "총 납입 원금": "원금", 
            "10년 후 순수 이자 (비과세)": "이자(비과세)", 
            "10년 후 총 환급액": "10년 후 환급액"
        }, inplace=True)
        
        # 표 스타일링
        st.dataframe(
            df.style.format({
                "원금": "{:,.0f}원",
                "이자(비과세)": "{:,.0f}원",
                "10년 후 환급액": "{:,.0f}원"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.header("🏦 은행 상품 환산 수익률")
        
        if len(bank_rates) > 0:
            for years, data in sorted(bank_rates.items()):
                with st.expander(f"**{years}년 납입** 환산 수익률 상세보기", expanded=True):
                    st.metric(
                        label=f"{years}년 납입 시 환산 적금 금리 (연, 세전 단리)", 
                        value=f"{data['rate']:.2f}%"
                    )
                    st.info(data['description'])
