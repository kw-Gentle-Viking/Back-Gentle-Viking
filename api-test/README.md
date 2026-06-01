# 프론트엔드 → 백엔드 전달 사항

## 변경 파일 목록

| 파일 | 상태 | 설명 |
|------|------|------|
| `app/routes_kis.py` | **신규 생성** | 한투 API 프록시 라우터 (전체 내용 참고) |
| `app/main.py` | **수정** | CORS 추가 + KIS 라우터 등록 |
| `app/rec_report.py` | **수정** | import 오타 수정 (1줄) |

---

## 1. app/routes_kis.py (신규)

한투 API를 프론트엔드에서 직접 호출하지 않고 백엔드가 프록시하는 라우터입니다.
`for-backend/app/routes_kis.py` 파일을 `app/` 폴더에 그대로 복사하면 됩니다.

### 제공하는 엔드포인트

| 메서드 | 경로 | 설명 | KIS TR ID |
|--------|------|------|-----------|
| GET | `/prices/current?code={종목코드}` | 현재가 조회 | VHKST01010100 (모의) |
| GET | `/prices/chart?code={종목코드}&range={범위}` | 일별 차트 | FHKST03010100 |
| GET | `/prices/intraday?code={종목코드}` | 당일 분봉 | FHKST03010200 |
| GET | `/market/volume-rank` | 거래량 순위 | FHPST01710000 (실전) |
| POST | `/trade/order` | 매수/매도 주문 | VTTC0012U/VTTC0011U (모의) |

### range 파라미터 값
`1D` `1W` `3M` `1Y` `5Y` `ALL`

### POST /trade/order 요청 바디
```json
{
  "code": "005930",
  "side": "buy",
  "qty": 10,
  "price": 70200,
  "price_type": "limit"
}
```
- `side`: `"buy"` | `"sell"`
- `price_type`: `"limit"` (지정가) | `"market"` (시장가, price=0)

### 필요한 .env 변수
```
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACC_NO=50158327-01
```

---

## 2. app/main.py 수정 사항

### 추가된 내용
```python
from fastapi.middleware.cors import CORSMiddleware
from app.routes_kis import router as kis_router

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kis_router, tags=["kis"])
```

> CORS의 `allow_origins`는 실제 배포 환경에 맞게 수정 필요합니다.

---

## 3. app/rec_report.py 수정 사항 (1줄)

Python 3.14에서 패키지명 대소문자 문제로 import 실패. 아래처럼 수정하면 됩니다.

```python
# 변경 전
import OpenDartReader

# 변경 후
import opendartreader as OpenDartReader
```

---

## 필요한 추가 패키지

기존 requirements에 없는 경우 설치 필요:

```bash
pip install httpx fastapi[all]
```
