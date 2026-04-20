"""
S&P 500 일목균형표 스크리너
주봉 기준 구름 돌파 종목 자동 탐색
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import time
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────
st.set_page_config(
    page_title="S&P 500 일목균형표 스크리너",
    page_icon="📊",
    layout="wide"
)

st.title("📊 S&P 500 일목균형표 스크리너")
st.caption("주봉 기준 · 구름 상향 돌파 · 양봉 종가 · MA20/MA60 구름 위")

# ──────────────────────────────────────────
# 1. S&P 500 티커 목록
# ──────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_sp500_tickers():
    """Wikipedia에서 S&P 500 구성 종목 로드 (1시간 캐시)"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "constituents"})
        tickers = []
        for row in table.findAll("tr")[1:]:
            ticker = row.findAll("td")[0].text.strip().replace(".", "-")
            tickers.append(ticker)
        return tickers
    except Exception as e:
        st.warning(f"티커 로드 실패, 샘플 목록 사용: {e}")
        return [
            "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA",
            "JPM","V","UNH","XOM","LLY","JNJ","MA","PG"
        ]


# ──────────────────────────────────────────
# 2. 일목균형표 계산
# ──────────────────────────────────────────
def calc_ichimoku(df):
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    tenkan   = (high.rolling(9).max()  + low.rolling(9).min())  / 2
    kijun    = (high.rolling(26).max() + low.rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)

    df = df.copy()
    df["tenkan"]       = tenkan
    df["kijun"]        = kijun
    df["senkou_a"]     = senkou_a
    df["senkou_b"]     = senkou_b
    df["cloud_top"]    = df[["senkou_a", "senkou_b"]].max(axis=1)
    df["cloud_bottom"] = df[["senkou_a", "senkou_b"]].min(axis=1)
    return df


# ──────────────────────────────────────────
# 3. 조건 검증
# ──────────────────────────────────────────
def check_conditions(df, breakout_lookback=4):
    df = df.dropna(subset=["cloud_top", "cloud_bottom"]).copy()
    if len(df) < 65:
        return False, {}

    last  = df.iloc[-1]
    close = df["Close"]

    # 조건 3: 양봉 + 구름 위 종가
    cond3_bullish     = bool(last["Close"] > last["Open"])
    cond3_above_cloud = bool(last["Close"] > last["cloud_top"])
    cond3 = cond3_bullish and cond3_above_cloud

    # 조건 4: MA20 / MA60 모두 구름 위
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma60 = float(close.rolling(60).mean().iloc[-1])
    cond4_ma20 = ma20 > float(last["cloud_top"])
    cond4_ma60 = ma60 > float(last["cloud_top"])
    cond4 = cond4_ma20 and cond4_ma60

    # 조건 2: 구름 상향 돌파 (lookback 주 이내)
    cond2 = False
    breakout_week  = None
    breakout_price = None
    window = df.iloc[-(breakout_lookback + 1):]
    for i in range(1, len(window)):
        prev = window.iloc[i - 1]
        curr = window.iloc[i]
        if prev["Close"] <= prev["cloud_top"] and curr["Close"] > curr["cloud_top"]:
            cond2 = True
            breakout_week  = curr.name
            breakout_price = float(curr["Close"])
            break

    passed = cond2 and cond3 and cond4

    detail = {
        "최신종가"         : round(float(last["Close"]), 2),
        "구름상단"         : round(float(last["cloud_top"]), 2),
        "구름하단"         : round(float(last["cloud_bottom"]), 2),
        "MA20"             : round(ma20, 2),
        "MA60"             : round(ma60, 2),
        "돌파일"           : str(breakout_week)[:10] if breakout_week else "-",
        "돌파가격"         : round(breakout_price, 2) if breakout_price else "-",
        "②구름돌파"        : "✅" if cond2 else "❌",
        "③양봉"           : "✅" if cond3_bullish else "❌",
        "③구름위종가"      : "✅" if cond3_above_cloud else "❌",
        "④MA20구름위"      : "✅" if cond4_ma20 else "❌",
        "④MA60구름위"      : "✅" if cond4_ma60 else "❌",
    }
    return passed, detail


# ──────────────────────────────────────────
# 4. 사이드바
# ──────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")

    breakout_lookback = st.slider(
        "돌파 인정 기간 (주)",
        min_value=1, max_value=8, value=4,
        help="몇 주 이내 구름 돌파를 인정할지. 1이면 이번 주 돌파만."
    )
    delay_sec = st.slider(
        "API 딜레이 (초)",
        min_value=0.1, max_value=1.0, value=0.3, step=0.1,
        help="yfinance 요청 간격. 너무 빠르면 차단될 수 있음."
    )

    st.divider()
    st.markdown("**📌 스크리닝 조건**")
    st.markdown("""
① 주봉(Weekly) 기준  
② 구름 상향 돌파  
③ 양봉 + 구름 위 종가  
④ MA20 / MA60 구름 위  
    """)

    st.divider()
    st.markdown("**📐 일목균형표 공식**")
    st.markdown("""
```
전환선  = (9주 고저) / 2
기준선  = (26주 고저) / 2
선행A   = (전환+기준)/2 → 26주↑
선행B   = (52주 고저)/2 → 26주↑
구름상단 = max(선행A, 선행B)
구름하단 = min(선행A, 선행B)
```
    """)


# ──────────────────────────────────────────
# 5. 스크리닝 실행
# ──────────────────────────────────────────
col1, col2 = st.columns([1, 3])
with col1:
    run_btn = st.button("🚀 스크리닝 시작", type="primary", use_container_width=True)

if run_btn:
    tickers = get_sp500_tickers()
    total   = len(tickers)

    st.info(f"S&P 500 {total}개 종목 분석 중... 약 3~5분 소요됩니다.")

    progress_bar = st.progress(0)
    status_text  = st.empty()

    results = []
    passed  = []

    for idx, ticker in enumerate(tickers, 1):
        try:
            raw = yf.download(
                ticker, period="2y", interval="1wk",
                progress=False, auto_adjust=True
            )
            if raw.empty or len(raw) < 65:
                continue

            df = calc_ichimoku(raw)
            ok, detail = check_conditions(df, breakout_lookback)

            if detail:
                row = {"티커": ticker, "통과": "✅" if ok else "❌", **detail}
                results.append(row)
                if ok:
                    passed.append(ticker)

        except Exception:
            pass

        progress_bar.progress(idx / total)
        status_text.text(f"분석 중... {idx} / {total}  |  통과 종목: {len(passed)}개")
        time.sleep(delay_sec)

    progress_bar.progress(1.0)
    status_text.text(f"✅ 완료!  전체 {total}개 분석  |  통과 {len(passed)}개")

    st.divider()

    # ── 통과 종목 ──────────────────────────────
    if passed:
        st.success(f"🎯 조건 통과 종목: **{len(passed)}개**")

        df_passed = pd.DataFrame([r for r in results if r["티커"] in passed])
        col_order = [
            "티커", "최신종가", "구름상단", "구름하단",
            "MA20", "MA60", "돌파일", "돌파가격",
            "②구름돌파", "③양봉", "③구름위종가", "④MA20구름위", "④MA60구름위"
        ]
        st.dataframe(
            df_passed[col_order],
            use_container_width=True,
            hide_index=True
        )

        csv_passed = df_passed.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 통과 종목 CSV 다운로드",
            data=csv_passed,
            file_name=f"ichimoku_passed_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("조건을 모두 만족하는 종목이 없습니다. 사이드바에서 돌파 인정 기간을 늘려보세요.")

    # ── 전체 결과 ──────────────────────────────
    if results:
        with st.expander("📋 전체 종목 결과 보기"):
            df_all = pd.DataFrame(results)
            st.dataframe(df_all, use_container_width=True, hide_index=True)

            csv_all = df_all.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 전체 결과 CSV 다운로드",
                data=csv_all,
                file_name=f"ichimoku_all_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
