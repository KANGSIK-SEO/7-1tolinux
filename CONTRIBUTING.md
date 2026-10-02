# 기여 가이드

`7-1tolinux`는 [AITOOLLEARN-7-1](https://github.com/KANGSIK-SEO/AITOOLLEARN-7-1) 텀프로젝트 챗봇을 커널/모듈
구조로 다시 짠 개인 오픈소스 파생 프로젝트입니다. 팀프로젝트 과제 규칙(커밋 수, 리뷰 담당자 등)은 여기 적용되지
않습니다 — 누구나 자유롭게 포크·PR·이슈를 보낼 수 있습니다.

## 가장 쉬운 기여: 새 미술관 모듈 추가
커널(`app/`, `app/kernel/`)은 거의 안 건드리고 끝나는 게 정상입니다.

1. `app/kernel/base.SourceModule`을 상속해 `fetch_all()`을 구현 (필요하면 `proxy_url`/`fetch_image_bytes`도).
2. `pyproject.toml`의 `[project.entry-points."sevenonelinux.modules"]`에 한 줄 등록.
3. `pip install -e .` 후 `7-1tolinux modules`로 보이는지, `7-1tolinux collect <이름>`으로 수집되는지 확인.
4. 테스트 추가(`tests/test_kernel.py` 참고), PR.

자세한 설계는 README의 "커널 vs 모듈" 절을 먼저 읽어주세요.

## 로컬 실행·테스트
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install -e .     # entry-point 기반 모듈 탐색에 필요
cp .env.example .env           # UPSTAGE_API_KEY, SECRET_KEY 채우기 (TURSO_*는 비워두면 로컬 SQLite)
.venv/bin/uvicorn app.main:app --reload
.venv/bin/python -m pytest -q tests
```
- PR을 올리기 전에 테스트가 통과해야 합니다. 새 기능에는 테스트를 함께 추가해 주세요.
- **비밀 값(`.env`, API 키, 토큰)은 절대 커밋하지 않습니다.**
- AI 모델은 `solar-pro4`만 허용되며 2027-04 이후 모든 모델이 차단됩니다(`app/config.py`). 다른 모델을 쓰고
  싶다면 이건 커널 정책(`app/config.py`)을 바꾸는 얘기라, 모듈 추가보다 더 큰 논의가 필요합니다 — 먼저 이슈로
  여세요.

## PR 작성 규칙
- 제목: `feat: 무엇을 왜` 한 줄. 본문: 변경 내용 / 확인 방법.
- 커널(`app/main.py`, `app/art.py`, `app/collect.py`, `db/schema.sql`)을 고쳐야 했다면 PR 설명에 **왜 모듈만으로는
  안 됐는지**를 적어주세요 — 커널 계약이 부족하다는 신호일 수 있어서, 그 자체가 중요한 피드백입니다.

## 개선 아이디어
- 새 미술관 모듈(Rijksmuseum, Getty 등 CC0/퍼블릭 도메인 공개 API)
- AI 모델도 플러그인화(`app/llm.py`를 `ModelModule` 같은 계약으로 분리) — 아직 미착수
- 답변이 "없다"고 하는데 관련 없는 작품 카드가 붙는 문제 (검색 관련도 필터)
- 모바일 화면·접근성, 로딩/오류 표시
- 검색 품질(동의어, 한국어 작가명 → 영문 변환), 테스트 보강
