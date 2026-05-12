# MHGN 실험용 Android 데이터 수집 앱 + Python risk API

이 패치는 현재 레포에 다음 구조를 추가한다.

```text
backend/
  app/main.py          FastAPI endpoint
  app/risk_model.py    pkl 모델 로드 + feature engineering + predict
  requirements.txt
android_demo/
  app/src/main/...     Kotlin/Compose 실험용 Android 앱
samples/
  user_features.example.json
me.py                  JSON 입력 지원 버전으로 교체
```

## 전체 흐름

```text
Android 앱
→ 오늘 하루 UsageStats / Call Log / SMS 수집
→ user_features.json 생성
→ Python FastAPI /predict-risk 로 전송
→ trained_models/*.pkl 로 risk score 예측
→ Android UI에 Health / Mental / Accident risk score 표시
```

## 현재 실제 수집되는 feature

- `total_screentime_hours`
- `time_spent_socialmedia_hours`
- `time_spent_game_hours`
- `first_phone_log_time_minutes`
- `last_phone_log_time_minutes`
- `night_screentime_hours`
- `number_calls`
- `total_call_duration_minutes`
- `variance_call_duration`
- `number_messages`

## 현재 기본값으로 들어가는 feature

아래 값들은 Health Connect/위치 추적 모듈을 아직 붙이지 않았기 때문에 기본값으로 들어간다.

- `mobility_time_hours`
- `resting_time_hours`
- `avg_sleep_time_hours`
- `var_sleep_time`
- `avg_heartrate_bpm`
- `var_heartrate`
- `number_steps`
- `distance_traveled_km`

이 값들도 모델 입력에는 들어가므로 앱은 정상적으로 예측을 받을 수 있다. 다만 발표할 때는 "현재 MVP에서는 앱 사용량/통화/SMS 중심 수집, 건강/위치 feature는 기본값 또는 향후 Health Connect 연동 예정"이라고 말하는 게 안전하다.

## Python 서버 실행

레포 루트에서 실행한다.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

테스트:

```bash
python me.py --input-json samples/user_features.example.json --output-json samples/result.example.json
```

## Android 앱 연결

- 에뮬레이터에서 Python 서버를 부르면 기본 URL은 `http://10.0.2.2:8000`
- 실기기에서 부르면 PC와 폰을 같은 Wi-Fi에 두고 `http://PC의_LAN_IP:8000` 입력
- 앱에서 `Usage access 열기`를 눌러 사용 정보 접근을 허용
- 앱에서 `Call/SMS 권한 요청`을 눌러 실험용 권한을 요청
- `데이터 수집 후 리스크 분석`을 누르면 JSON 생성, 서버 전송, 점수 표시가 진행된다

## 주의

- `READ_CALL_LOG`, `READ_SMS`는 기기/Android 버전/설치 방식에 따라 직접 설치 앱에서도 거부될 수 있다
- Google Play 배포용이 아니라 Android Studio 직접 설치 시연용 구조다
- `trained_models/` 폴더와 `feature_columns.pkl`은 기존 레포의 파일을 그대로 사용한다
