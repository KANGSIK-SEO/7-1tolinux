"""레지스트리에 등록된 SourceModule 하나를 돌려 그 결과를 art.db에 반영하는 공용 로직.
모듈 쪽은 ArtworkRecord만 yield하면 되고, "어디에 어떻게 저장하는가"는 전부 여기(커널 쪽
서비스)가 책임진다 — 수집 로직과 저장 로직을 분리해야 새 모듈을 추가할 때 이 파일을 안
건드려도 된다.
"""
import sqlite3
from dataclasses import asdict

from .config import ROOT

DB_PATH = ROOT / "data" / "art.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"

COLUMNS = (
    "source", "source_id", "title", "artist", "artist_bio", "date_display",
    "year_start", "year_end", "medium", "classification", "department", "origin",
    "style", "subjects", "image_url", "thumbnail_url", "source_url", "credit_line",
    "is_public_domain", "license", "is_highlight",
)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def _upsert(conn, record) -> None:
    row = asdict(record)
    row["is_public_domain"] = int(row["is_public_domain"])
    row["is_highlight"] = int(row["is_highlight"])
    placeholders = ", ".join("?" for _ in COLUMNS)
    updates = ", ".join(f"{c}=excluded.{c}" for c in COLUMNS if c not in ("source", "source_id"))
    conn.execute(
        f"INSERT INTO artworks ({', '.join(COLUMNS)}) VALUES ({placeholders}) "
        f"ON CONFLICT(source, source_id) DO UPDATE SET {updates}",
        [row.get(c) for c in COLUMNS],
    )


def collect_source(module, limit: int = 0, progress=print) -> int:
    """module.fetch_all()이 yield하는 작품을 전부 art.db에 upsert하고 저장 건수를 돌려준다."""
    conn = _connect()
    saved = 0
    try:
        for record in module.fetch_all(limit=limit):
            _upsert(conn, record)
            saved += 1
            if saved % 100 == 0:
                conn.commit()
                progress(f"  [{module.source}] 저장 {saved}건…")
        conn.commit()
    finally:
        conn.close()
    progress(f"[{module.source}] 완료: 저장 {saved}건")
    return saved
