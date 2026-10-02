"""커널(모듈 레지스트리)과 collect.py에 대한 테스트. pip install -e . 로 entry-point가
설치돼 있어야 레지스트리가 met/aic 모듈을 찾는다(패키지 메타데이터 기반 탐색이라서)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234")

from app import collect  # noqa: E402
from app.kernel.base import ArtworkRecord, ImageUnavailable, SourceModule  # noqa: E402
from app.kernel.registry import get_registry, reset_registry_for_tests  # noqa: E402


def test_registry_discovers_installed_modules():
    sources = {m.source for m in get_registry().list()}
    assert sources == {"met", "aic"}


def test_registry_is_keyed_by_source_slug():
    registry = get_registry()
    assert registry.get("aic").__class__.__name__ == "AicModule"
    assert registry.get("does-not-exist") is None


def test_source_module_default_has_no_proxy():
    """커널 기본 구현: 프록시가 필요 없는 모듈은 proxy_url이 None을 돌려줘야 원본 URL을 쓴다."""

    class PlainModule(SourceModule):
        source = "plain"

        def fetch_all(self, limit=0):
            return iter(())

    m = PlainModule()
    assert m.proxy_url({"source": "plain", "image_url": "https://x/y.jpg"}, 400) is None


def test_image_unavailable_carries_status():
    err = ImageUnavailable(502, "boom")
    assert err.status == 502 and str(err) == "boom"


def test_collect_source_upserts_records_into_art_db(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "DB_PATH", tmp_path / "art.db")

    class _FakeModule(SourceModule):
        source = "fake"

        def fetch_all(self, limit=0):
            yield ArtworkRecord(source="fake", source_id="1", title="Test Work",
                                image_url="https://x/1.jpg", source_url="https://x/1")

    saved = collect.collect_source(_FakeModule(), progress=lambda *_: None)
    assert saved == 1

    import sqlite3
    conn = sqlite3.connect(tmp_path / "art.db")
    row = conn.execute("SELECT title, source, is_public_domain FROM artworks WHERE source='fake'").fetchone()
    conn.close()
    assert row == ("Test Work", "fake", 1)


def test_reset_registry_for_tests_forces_reload():
    first = get_registry()
    reset_registry_for_tests()
    second = get_registry()
    assert first is not second
    assert {m.source for m in second.list()} == {"met", "aic"}
