# 📊 S&P 500 일목균형표 스크리너

주봉 기준으로 일목균형표 구름 돌파 종목을 자동 탐색하는 Streamlit 앱입니다.

## 스크리닝 조건

1. **주봉 기준** - 모든 조건을 주봉(Weekly)에서 판단
2. **구름 상향 돌파** - 최근 N주 이내 구름 상단을 아래에서 위로 돌파
3. **양봉 + 구름 위 종가** - 최신 주봉이 양봉이며 종가가 구름 위
4. **MA20 / MA60 구름 위** - 20주·60주 이동평균선이 모두 구름 상단 위

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포

1. 이 저장소를 GitHub에 Push
2. [streamlit.io/cloud](https://streamlit.io/cloud) 접속 후 로그인
3. **New app** → 저장소 선택 → Main file: `app.py` → Deploy
