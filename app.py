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
    
    premium = st.number_input(
        "월 보험료 (원)", 
        min_value=0,
        value=None,
        step=10000,
        placeholder="예: 131000",
        help="매월 납입할 보험료를 입력하세요."
    )
    
    rate_pct = st.number_input(
        "10년 시점 환급률 (%)", 
        min_value=0.0, 
        value=None,
        step=0.1, 
        format="%.1f",
        placeholder="예: 119.1",
        help="보험설계서 상의 10년 시점 환급률을 입력하세요. 납입기간과 관계없이 10년째의 환급률입니다."
    )
    
    st.write("납입기간 선택 (중복 선택 가능)")
    selected_periods = {}
    selected_periods[TERMS[0]] = st.checkbox(f"{TERM_LABELS[0]} 납입 (+5년 거치)", value=False)
    selected_periods[TERMS[1]] = st.checkbox(f"{TERM_LABELS[1]} 납입 (+3년 거치)", value=False)
    selected_periods[TERMS[2]] = st.checkbox(f"{TERM_LABELS[2]} 납입 (거치 없음)", value=False)
    selected_periods[TERMS[3]] = st.checkbox(f"{TERM_LABELS[3]} 납입 (거치 없음)", value=False)
    
    st.write("") # 여백
    submitted = st.form_submit_button("계산 실행하기", type="primary", use_container_width=True)

# --- 계산 버튼 클릭 후 결과 표시 ---
if submitted:
    if premium is None or rate_pct is None or premium <= 0 or rate_pct <= 0:
        st.error("월 보험료와 환급률을 0보다 큰 값으로 입력해주세요.")
    elif not any(selected_periods.values()):
        st.warning("계산할 납입기간을 하나 이상 선택해주세요.")
    else:
        results_data = []
        bank_rates = {}

        for years, is_selected in selected_periods.items():
            if not is_selected:
                continue

            months = years * 12
            principal_sum = premium * months
            insurance_total_at_10_years = principal_sum * (rate_pct / 100.0)
            interest_ins = insurance_total_at_10_years - principal_sum

            results_data.append({
                "납입 기간": f"{years}년",
                "총 납입 원금": principal_sum,
                "10년 후 순수 이자 (비과세)": interest_ins,
                "10년 후 총 환급액": insurance_total_at_10_years
            })

            # --- 은행 상품과 비교를 위한 환산 금리 계산 로직 (역산) ---
            equivalent_pre_tax_interest = interest_ins / (1 - TAX_RATE) if (1 - TAX_RATE) > 0 else 0
            total_pre_tax_value = principal_sum + equivalent_pre_tax_interest

            bank_r = 0
            description = ""
            details = {}

            if years < 10:
                grace_years = 10 - years
                deposit_factor = (1 + DEPOSIT_RATE) ** grace_years
                
                value_before_deposit = total_pre_tax_value / deposit_factor
                interest_during_saving_period = value_before_deposit - principal_sum
                
                denom = premium * (months * (months + 1) / 24.0)
                bank_r = interest_during_saving_period / denom if denom > 0 else 0
                bank_pct = bank_r * 100
                
                description = (
                    f"이 보험 상품은 **{years}년 동안 연 {bank_pct:.2f}% 단리 적금**에 가입하고, "
                    f"만기된 원리금(세전)을 **{grace_years}년 동안 연 {DEPOSIT_RATE*100:.0f}% 복리 예금**에 "
                    "거치했을 때와 동일한 수익률입니다."
                )
                details = {
                    "is_deposit_model": True,
                    "principal": principal_sum,
                    "insurance_refund": insurance_total_at_10_years,
                    "months": months
                }
            else: # years >= 10
                interest_during_saving_period = equivalent_pre_tax_interest
                
                denom = premium * (months * (months + 1) / 24.0)
                bank_r = interest_during_saving_period / denom if denom > 0 else 0
                bank_pct = bank_r * 100
                
                description = (
                    f"이 보험 상품의 수익률은 **연 {bank_pct:.2f}%짜리 {years}년 만기 일반과세 단리 적금**"
                    " 상품과 동일한 수익률입니다."
                )
                details = {
                    "is_deposit_model": False,
                    "principal": principal_sum,
                    "insurance_refund": insurance_total_at_10_years,
                    "months": months
                }
            
            bank_rates[years] = { "rate": bank_pct, "description": description, "details": details }
        
        st.write("---")
        st.header("📊 계산 결과 요약")
        
        df = pd.DataFrame(results_data)
        df.rename(columns={
            "총 납입 원금": "원금", 
            "10년 후 순수 이자 (비과세)": "이자(비과세)", 
            "10년 후 총 환급액": "10년 후 환급액"
        }, inplace=True)
        
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
                details = data['details']
                with st.expander(f"**{years}년 납입** 환산 수익률 상세보기", expanded=True):
                    st.metric(
                        label=f"{years}년 납입 시 환산 적금 금리 (연, 세전 단리)", 
                        value=f"{data['rate']:.2f}%"
                    )
                    st.info(data['description'])

                    st.subheader("🧮 환산 계산 상세 내역 (세후 기준)")

                    # --- 상세 내역 표시를 위한 정방향 재계산 로직 (수정됨) ---
                    principal = details['principal']
                    months = details['months']
                    
                    # BUG FIX: 표시되는 이자율(소수점 2자리)을 기준으로 재계산
                    rounded_pct = round(data['rate'], 2)
                    rounded_rate = rounded_pct / 100.0

                    # 1. 적금 기간 이자 계산 (정방향, 네이버 계산기 방식)
                    # 1-1. 세전 이자 계산 후 반올림
                    savings_interest_pre_tax_float = premium * (months * (months + 1) / 2) * (rounded_rate / 12)
                    savings_interest_pre_tax = round(savings_interest_pre_tax_float)
                    
                    # 1-2. 세금 계산 후 반올림
                    tax_on_savings = round(savings_interest_pre_tax * TAX_RATE)
                    
                    # 1-3. 세후 이자 계산
                    savings_interest_after_tax = savings_interest_pre_tax - tax_on_savings
                    savings_total_after_tax = principal + savings_interest_after_tax

                    # 2. 예금 거치 기간 이자 계산 (정방향)
                    deposit_interest_after_tax = 0
                    final_total_after_tax = savings_total_after_tax

                    if details['is_deposit_model']:
                        grace_years = 10 - years
                        # 예금 이자는 '세후' 원리금을 기준으로 다시 복리 계산
                        deposit_base_amount = savings_total_after_tax
                        
                        # 예금 이자도 단계별로 세금 계산
                        deposit_total_pre_tax = deposit_base_amount * ((1 + DEPOSIT_RATE) ** grace_years)
                        deposit_interest_pre_tax = deposit_total_pre_tax - deposit_base_amount
                        tax_on_deposit = round(deposit_interest_pre_tax * TAX_RATE)
                        deposit_interest_after_tax = round(deposit_interest_pre_tax - tax_on_deposit)

                        final_total_after_tax = savings_total_after_tax + deposit_interest_after_tax


                    if details['is_deposit_model']:
                        grace_years = 10 - years
                        st.markdown(f"**1. 적금 기간 ({years}년, 연 {data['rate']:.2f}%)**")
                        st.markdown(f"""
                        - 납입 원금: `{principal:,.0f}원`
                        - 발생 이자 (세후): `{savings_interest_after_tax:,.0f}원`
                        - **{years}년 후 원리금 합계 (A) (세후):** `{savings_total_after_tax:,.0f}원`
                        """)
                        
                        st.markdown(f"**2. 예금 거치 기간 ({grace_years}년, 연 {DEPOSIT_RATE*100:.0f}%)**")
                        st.markdown(f"""
                        - 거치 원금 (A): `{savings_total_after_tax:,.0f}원`
                        - 발생 이자 (세후): `{deposit_interest_after_tax:,.0f}원`
                        """)
                        
                        st.markdown(f"**3. 최종 결과 (10년 후)**")
                        st.markdown(f"""
                        - **은행 상품 총 원리금 (세후):** `{final_total_after_tax:,.0f}원`
                        - **보험 상품 총 환급액 (비과세):** `{details['insurance_refund']:,.0f}원`
                        """)
                    else: # 적금만 있는 경우
                        st.markdown(f"**1. 적금 기간 ({years}년, 연 {data['rate']:.2f}%)**")
                        st.markdown(f"""
                        - 납입 원금: `{principal:,.0f}원`
                        - 발생 이자 (세후): `{savings_interest_after_tax:,.0f}원`
                        """)
                        
                        st.markdown(f"**2. 최종 결과 ({years}년 후)**")
                        st.markdown(f"""
                        - **은행 상품 총 원리금 (세후):** `{final_total_after_tax:,.0f}원`
                        - **보험 상품 총 환급액 (비과세):** `{details['insurance_refund']:,.0f}원`
                        """)
                    
                    # 최종 실수령액 비교 설명
                    final_diff = final_total_after_tax - details['insurance_refund']

                    st.success(f"**최종 수익률 비교:** 위 계산에 따른 은행 상품의 최종 세후 금액과 보험 환급액의 차이는 **`{final_diff:,.0f}원`** 입니다. 이 차이가 0에 가까울수록 환산된 이자율이 정확함을 의미합니다.")
