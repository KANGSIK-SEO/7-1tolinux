# 7-1tolinux

[AITOOLLEARN-7-1](https://github.com/KANGSIK-SEO/AITOOLLEARN-7-1) 텀프로젝트 챗봇("저작권 걱정 없는 퍼블릭 도메인
명화 찾기")을 **Linux 커널/드라이버 철학**으로 다시 짠 파생 프로젝트입니다. 원본 텀프로젝트는 그대로 두고, 여기서는
"미술관 출처 하나하나"를 커널에 꽂는 **모듈(드라이버)** 로 바꿉니다.

## 왜 리눅스처럼 만드는가
Linux 커널이 배포판·데스크톱환경과 분리돼 있어서 아무나 디바이스 드라이버를 보탤 수 있었던 것처럼, 이 프로젝트는
**무료로 공개**하고 **커널(핵심 파이프라인)과 모듈(미술관 커넥터)을 분리**합니다. 누가 어떤 미술관의 모듈을 짜서
보태도 커널 코드는 한 줄도 안 건드려도 됩니다 — 진입장벽이 낮을수록 더 많은 사람이 부담 없이 업그레이드해주고,
그게 한 사람에게 유지보수가 몰리지 않는 **지속가능성**으로 이어진다는 베팅입니다. (같은 철학을 미술품 위작 검증
쪽에 적용한 자매 프로젝트: [art_linux](https://github.com/KANGSIK-SEO/art_linux) — `VerificationModule` 커널.)

## 커널 vs 모듈
| | 커널 (`app/`, `app/kernel/`) | 모듈 (`app/modules/`) |
|---|---|---|
| 안다 | "미술관 출처 하나는 `SourceModule` 계약을 지킨다"는 것만 | 그 미술관 API의 실제 모양(필드명, 페이징, 레이트리밋, 이미지 접근 방식) |
| 모른다 | MET이 뭔지, AIC가 뭔지 | 다른 모듈이 뭘 하는지 |
| 바뀌는 빈도 | 거의 없음 | 미술관마다, 자주 |

```python
# app/kernel/base.py — 커널이 요구하는 전부
class SourceModule(ABC):
    source: str                                      # artworks.source 슬러그
    def fetch_all(self, limit=0) -> Iterator[ArtworkRecord]: ...   # 수집
    def proxy_url(self, work, width) -> str | None: ...            # 이미지 프록시가 필요하면 경로, 아니면 None
    def fetch_image_bytes(self, image_id, width) -> tuple[bytes, str]: ...  # 프록시 호출 시 실제 페치
```

새 미술관을 추가하고 싶은 사람은 `SourceModule`을 구현하고 `pyproject.toml`의
`[project.entry-points."sevenonelinux.modules"]`에 한 줄 등록하면 끝입니다 — `apt`로 드라이버를 깔면 커널이
`lsmod`로 보는 것과 같은 방식으로, `app/kernel/registry.py`가 Python entry-point를 스캔해 자동으로 찾습니다.

```bash
7-1tolinux modules              # lsmod처럼 설치된 모듈 나열
# aic        app.modules.aic.AicModule
# met        app.modules.met.MetModule

7-1tolinux collect met --limit 50   # met 모듈만 돌려 art.db에 반영
7-1tolinux collect                  # 설치된 모듈 전체 수집
```

**내장 모듈 2개**
- `app/modules/met.py` — MET Open Access. 이미지가 공개 URL이라 프록시 불필요(`proxy_url`이 `None`).
- `app/modules/aic.py` — Art Institute of Chicago. 이미지 서버가 전용 헤더(`AIC-User-Agent`) 없이는 403을 줘서
  서버가 대신 받아 중계해야 한다 — 같은 `SourceModule` 계약 안에서도 모듈마다 "하드웨어 특이사항"이 다르다는 걸
  보여주는 지점.

DB 스키마(`db/schema.sql`)는 `source` 컬럼 값을 미리 고정하지 않습니다(`CHECK (source IN (...))` 같은 제약을
일부러 안 씁니다) — 커널이 어떤 모듈이 꽂힐지 미리 알면 그 자체가 진입장벽이기 때문입니다.

## 그 위의 챗봇 서비스 (원본 텀프로젝트와 동일)
"상업적으로 써도 되는 명화"를 한국어로 물어보면, 커널이 모은 **CC0(퍼블릭 도메인) 작품 DB**에서 근거를 찾아
답하고 원본 이미지·출처 링크를 카드로 보여주는 FastAPI 웹 챗봇입니다. 챗봇 기능 자체는 바뀌지 않았고, 내부에서
미술관 출처를 다루는 방식만 모듈화했습니다.

- **핵심 시나리오**: 로그인 → "봄 느낌 풍경화 3개, 상업적으로 써도 되는 걸로" → 작품 카드(썸네일·작가·연도·CC0·
  원본/출처 링크) + 한국어 설명
- **초대코드(프리미엄)**: 회원가입 시 `private_code`가 `PREMIUM_CODE`(서버 환경변수)와 일치하면 그 계정은
  시간당 질문 한도가 올라가고(`CHAT_LIMIT_PER_HOUR_PREMIUM`, 기본 300 vs 일반 30), 평생 무료 질문 100회
  제한(`CHAT_LIFETIME_LIMIT_FREE`)이 면제되며, 추천 작품 수가 늘고(`ART_RESULTS_LIMIT_PREMIUM`, 기본 100 vs
  일반 6), 화면이 화이트 테마로 바뀐다. 코드 입력 UI는 로그인이 아니라 **회원가입** 화면에만 있다.

### 컴포넌트
| 파일 | 역할 |
|---|---|
| `app/main.py` | 라우팅, 입력 검증, 로그, 오류 응답. 이미지 프록시는 `/api/img/<source>/<id>`로 일반화해 해당 모듈에 위임 |
| `app/auth.py` | 비밀번호 해시(scrypt) + HMAC 서명 쿠키. 서버에 세션을 저장하지 않음 |
| `app/chat.py` | "질문 → 검색조건 추출 → 검색 → 답변 생성" 파이프라인 |
| `app/art.py` | `data/art.db`를 SQLite FTS5로 검색. 이미지 프록시 필요 여부는 레지스트리에 위임해 커널이 소스를 모름 |
| `app/llm.py` | Upstage `solar-pro4` 호출(서버 전용, 타임아웃 설정) |
| `app/db.py` | 사용자·대화 로그 DB (Turso 또는 로컬 SQLite 자동 선택) |
| `app/config.py` | 허용 모델·만료일·레이트리밋 등 정책 |
| `app/kernel/base.py` | `SourceModule`/`ArtworkRecord`/`ImageUnavailable` — 커널 계약 |
| `app/kernel/registry.py` | entry-point 자동 탐색 (`lsmod`) |
| `app/collect.py` | 모듈이 yield한 `ArtworkRecord`를 `art.db`에 upsert (수집 로직과 저장 로직 분리) |
| `app/cli.py` | `7-1tolinux modules` / `7-1tolinux collect` |

```
브라우저 ─ /static (HTML/JS) ─┐
                              ├─ FastAPI (app/main.py)
  POST /api/chat ─────────────┘    ├─ 인증: scrypt 해시 + HMAC 서명 쿠키 (app/auth.py)
                                   ├─ chat.extract_intent → solar-pro4 (검색 조건 JSON)
                                   ├─ art.search → data/art.db (읽기 전용 SQLite + FTS5)
                                   │     └─ 이미지 프록시 필요 여부 → kernel.registry → SourceModule
                                   ├─ chat.compose_answer → solar-pro4 (근거 기반 한국어 답변)
                                   └─ db.execute → Turso(SQLite 호환): users, chats

7-1tolinux collect [source] ─ kernel.registry가 설치된 SourceModule을 찾음
                             └─ module.fetch_all() → app/collect.py가 art.db에 upsert
```

## API 명세
오류는 항상 `{"error": {"code": "...", "message": "..."}}`.

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/auth/signup` | `{email, password(8자+), private_code?}` → 201, 세션 쿠키 발급 |
| POST | `/api/auth/login` | 로그인 → 200, 세션 쿠키 |
| POST | `/api/auth/logout` | 쿠키 삭제 |
| GET | `/api/me` | 현재 사용자 |
| POST | `/api/chat` | **로그인 필요**. 질문 → 답변 + 작품 카드 |
| GET | `/api/me/chats?limit=20&offset=0` | 내 대화 로그 조회 |
| GET | `/api/img/{source}/{image_id}?w=` | 소스 모듈에 위임하는 이미지 프록시. 모듈이 지원 안 하면 404 `PROXY_NOT_SUPPORTED` |
| GET | `/api/health` | 상태 확인 |

오류 코드: `UNAUTHENTICATED`(401) `EMPTY_MESSAGE`/`MESSAGE_TOO_LONG`(400) `RATE_LIMITED`(429)
`FREE_LIMIT_REACHED`(403) `AI_TIMEOUT`(504) `AI_ERROR`(502) `AI_EXPIRED`/`AI_MODEL_NOT_ALLOWED`/`AI_KEY_MISSING`(503)
`DB_ERROR`/`ART_DB_ERROR`(503) `UNKNOWN_SOURCE`/`PROXY_NOT_SUPPORTED`/`IMAGE_UNAVAILABLE`(404/502/400)

## DB 구조
- `data/art.db` (읽기 전용, 레포에 포함): `artworks`(source, source_id, title, artist, date_display, medium,
  subjects, image_url, source_url, license, is_public_domain …) + `artworks_fts`(FTS5). 스키마: `db/schema.sql`.
  `source` 컬럼은 특정 값으로 고정돼 있지 않다(모듈이 늘어도 스키마를 안 건드리기 위함).
- Turso/SQLite (쓰기):
  - `users(id, email UNIQUE, password_hash, is_premium, created_at)`
  - `chats(id, user_id → users.id, question, answer, status[ok|error], error_code, latency_ms, artwork_ids(JSON), created_at)`

**DB 확인 가이드**
1. 로그 조회 API: `curl -b cookies.txt https://<서비스>/api/me/chats`
2. 확인용 SQL: `scripts/check_logs.sql`
3. 서버 로그: `request_received`, `ai_call_start`, `ai_call_success|ai_call_failure`, `db_save_success|db_save_failure`

## 실행·개발
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install -e .        # 모듈 entry-point를 레지스트리가 찾으려면 editable install 필요
cp .env.example .env              # 값 채우기
.venv/bin/uvicorn app.main:app --reload    # http://localhost:8000
.venv/bin/python -m pytest -q tests
.venv/bin/7-1tolinux modules      # 설치된 모듈 확인
.venv/bin/7-1tolinux collect met --limit 50   # art.db에 MET 작품 50건 수집
```

Docker/Vercel 배포 절차는 원본 AITOOLLEARN-7-1과 동일합니다(`Dockerfile`, `deploy/Dockerfile`, `vercel.json`).
이 리포는 독립 배포용이 아니라 아키텍처 실험용이라 기본적으로 별도 호스팅을 두진 않습니다 — 포크해서 자기
인스턴스를 띄우는 것도 "리눅스처럼" 쓰는 방법 중 하나입니다.

**환경 변수** (`.env.example` 참고, 값은 절대 커밋하지 않는다)

| 이름 | 설명 |
|---|---|
| `UPSTAGE_API_KEY` | Upstage solar-pro4 키 |
| `SECRET_KEY` | 세션 서명 키 (32자 이상 랜덤) |
| `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` | Turso DB. 없으면 로컬 `data/app.db` 사용 |
| `LLM_TIMEOUT_SECONDS` | AI 호출 타임아웃(기본 20) |
| `PREMIUM_CODE` | 회원가입 시 입력받는 초대코드(선택) |
| `CHAT_LIMIT_PER_HOUR_PREMIUM` | 초대코드 사용자 시간당 질문 상한(기본 300) |
| `CHAT_LIFETIME_LIMIT_FREE` | 초대코드 없는 사용자의 평생 무료 질문 수(기본 100) |
| `ART_RESULTS_LIMIT_PREMIUM` | 초대코드 사용자에게 보여줄 추천 작품 수(기본 100) |

## 새 미술관 모듈 만들기
1. `app/kernel/base.SourceModule`을 상속해 `fetch_all()`을 구현한다(필요하면 `proxy_url`/`fetch_image_bytes`도).
2. `pyproject.toml`의 `[project.entry-points."sevenonelinux.modules"]`에 `이름 = "패키지.모듈:클래스"` 한 줄 등록.
3. `pip install -e .` 후 `7-1tolinux modules`로 보이는지 확인, `7-1tolinux collect <이름>`으로 수집.
4. 커널 쪽 코드(`app/main.py`, `app/art.py`, `app/collect.py`, `db/schema.sql`)는 건드릴 필요가 없다 — 건드려야
   했다면 그건 커널 계약(`SourceModule`)이 부족하다는 신호다.

## 민감정보 관리
- 모든 키는 환경 변수로만 사용하고 `.env`는 `.gitignore`로 제외한다. 예시는 `.env.example`.
- AI 호출은 서버에서만 수행되며 키는 응답·로그에 노출되지 않는다.
- **모델 정책**: `solar-pro4` 외 모델 호출은 코드에서 차단, 2027-04 이후에는 모든 모델 호출이 차단된다
  (`app/config.py`).

## 라이선스
MIT — 카피레프트보다 생태계 확산 속도를 우선한 선택. 자세한 배경은 [art_linux](https://github.com/KANGSIK-SEO/art_linux)
README 참고.
