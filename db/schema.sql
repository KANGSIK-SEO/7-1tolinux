-- 미술 작품 DB (읽기 전용 데이터). 어떤 출처가 쓸지 스키마가 미리 알 필요는 없다 — 설치된
-- 소스 모듈(app/modules/*, `sevenonelinux.modules` entry-point)이 각자 수집해 채운다.
-- 내장 모듈: met(MET Open Access, CC0), aic(Art Institute of Chicago API, CC0).
-- 수집 실행: `7-1tolinux collect [소스] [--limit N]` (app/cli.py → app/collect.py)

CREATE TABLE IF NOT EXISTS artworks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source           TEXT    NOT NULL,  -- 모듈의 SourceModule.source 슬러그. 커널은 어떤 값이 올지 모른다(미리 고정하면 새 모듈을 못 꽂는다).
    source_id        TEXT    NOT NULL,          -- 출처 기관에서의 작품 ID
    title            TEXT    NOT NULL,
    artist           TEXT,
    artist_bio       TEXT,                      -- 예: "Dutch, Zundert 1853–1890 Auvers-sur-Oise"
    date_display     TEXT,                      -- 표기용 제작 시기
    year_start       INTEGER,
    year_end         INTEGER,
    medium           TEXT,
    classification   TEXT,
    department       TEXT,
    origin           TEXT,                      -- 제작 국가/문화권
    style            TEXT,
    subjects         TEXT,                      -- 쉼표로 구분한 주제 키워드 (landscape, flowers ...)
    image_url        TEXT    NOT NULL,          -- 큰 이미지 (공식 URL)
    thumbnail_url    TEXT,
    source_url       TEXT    NOT NULL,          -- 기관 공식 작품 페이지
    credit_line      TEXT,
    is_public_domain INTEGER NOT NULL DEFAULT 1 CHECK (is_public_domain IN (0, 1)),
    license          TEXT    NOT NULL DEFAULT 'CC0',
    is_highlight     INTEGER NOT NULL DEFAULT 0,
    collected_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_artworks_artist ON artworks (artist);
CREATE INDEX IF NOT EXISTS idx_artworks_year   ON artworks (year_start, year_end);
CREATE INDEX IF NOT EXISTS idx_artworks_pd     ON artworks (is_public_domain);

-- 자연어 질문에서 뽑은 키워드로 검색하기 위한 전문 검색 인덱스
CREATE VIRTUAL TABLE IF NOT EXISTS artworks_fts USING fts5 (
    title, artist, medium, style, subjects, origin,
    content = 'artworks', content_rowid = 'id', tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS artworks_ai AFTER INSERT ON artworks BEGIN
    INSERT INTO artworks_fts (rowid, title, artist, medium, style, subjects, origin)
    VALUES (new.id, new.title, new.artist, new.medium, new.style, new.subjects, new.origin);
END;

CREATE TRIGGER IF NOT EXISTS artworks_ad AFTER DELETE ON artworks BEGIN
    INSERT INTO artworks_fts (artworks_fts, rowid, title, artist, medium, style, subjects, origin)
    VALUES ('delete', old.id, old.title, old.artist, old.medium, old.style, old.subjects, old.origin);
END;

CREATE TRIGGER IF NOT EXISTS artworks_au AFTER UPDATE ON artworks BEGIN
    INSERT INTO artworks_fts (artworks_fts, rowid, title, artist, medium, style, subjects, origin)
    VALUES ('delete', old.id, old.title, old.artist, old.medium, old.style, old.subjects, old.origin);
    INSERT INTO artworks_fts (rowid, title, artist, medium, style, subjects, origin)
    VALUES (new.id, new.title, new.artist, new.medium, new.style, new.subjects, new.origin);
END;
