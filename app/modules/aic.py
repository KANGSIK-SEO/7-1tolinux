"""AIC 드라이버: Art Institute of Chicago API에서 퍼블릭 도메인 회화를 가져온다.
API 키 불필요. 이 소스는 다른 모듈과 달리 전용 헤더(AIC-User-Agent) 없이는 이미지 서버가
403을 돌려주고, 브라우저 <img>는 커스텀 헤더를 못 붙이므로 fetch_image_bytes로 서버가 대신
받아 중계한다 — "같은 ArtworkRecord 계약 안에서도 모듈마다 하드웨어 특이사항이 다르다"는
art_linux 커널 철학이 그대로 적용되는 지점.
"""
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterator

from ..kernel.base import ArtworkRecord, ImageUnavailable, SourceModule

BASE = "https://api.artic.edu/api/v1"
IIIF = "https://www.artic.edu/iiif/2"
USER_AGENT_SEARCH = "7-1tolinux aic-module"
USER_AGENT_IMAGE = "7-1tolinux/1.0 (student project; https://github.com/KANGSIK-SEO/7-1tolinux)"
FIELDS = ",".join([
    "id", "title", "artist_display", "artist_title", "date_display", "date_start", "date_end",
    "medium_display", "classification_title", "department_title", "place_of_origin",
    "style_title", "subject_titles", "image_id", "is_public_domain", "credit_line",
])
PAGE_SIZE = 100
# AIC 검색 API는 한 질의에서 1000건까지만 조회되므로(초과 시 403) 제작 시기 구간으로 나눠 수집한다.
WINDOWS = [(None, 1600)] + [(y, y + 50) for y in range(1600, 2000, 50)] + [(2000, None)]

IMAGE_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
IMAGE_URL_RE = re.compile(r"/iiif/2/([0-9a-f-]{36})/")
ALLOWED_WIDTHS = {200, 400, 843, 1686}


def _get_json(url: str, params: dict | None = None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT_SEARCH})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _window_filters(lo, hi) -> dict:
    f = {
        "query[bool][must][0][term][is_public_domain]": "true",
        "query[bool][must][1][term][classification_titles.keyword]": "painting",
    }
    n = 2
    if lo is not None:
        f[f"query[bool][must][{n}][range][date_start][gte]"] = lo
        n += 1
    if hi is not None:
        f[f"query[bool][must][{n}][range][date_start][lt]"] = hi
    return f


def _to_record(a: dict) -> ArtworkRecord | None:
    if not a.get("is_public_domain") or not a.get("image_id") or not a.get("title"):
        return None
    image_id = a["image_id"]
    return ArtworkRecord(
        source="aic",
        source_id=str(a["id"]),
        title=a["title"],
        image_url=f"{IIIF}/{image_id}/full/1686,/0/default.jpg",
        source_url=f"https://www.artic.edu/artworks/{a['id']}",
        artist=a.get("artist_title") or None,
        artist_bio=a.get("artist_display") or None,
        date_display=a.get("date_display") or None,
        year_start=a.get("date_start"),
        year_end=a.get("date_end"),
        medium=a.get("medium_display") or None,
        classification=a.get("classification_title") or None,
        department=a.get("department_title") or None,
        origin=a.get("place_of_origin") or None,
        style=a.get("style_title") or None,
        subjects=", ".join(a.get("subject_titles") or []) or None,
        thumbnail_url=f"{IIIF}/{image_id}/full/400,/0/default.jpg",
        credit_line=a.get("credit_line") or None,
    )


class AicModule(SourceModule):
    source = "aic"

    def fetch_all(self, limit: int = 0) -> Iterator[ArtworkRecord]:
        saved = 0
        for lo, hi in WINDOWS:
            page = 1
            while True:
                data = _get_json(f"{BASE}/artworks/search", {
                    **_window_filters(lo, hi), "fields": FIELDS, "limit": PAGE_SIZE, "page": page,
                })
                items = (data or {}).get("data") or []
                if not items:
                    break
                for item in items:
                    record = _to_record(item)
                    if record is not None:
                        yield record
                        saved += 1
                        if limit and saved >= limit:
                            return
                pg = data["pagination"]
                if page >= pg["total_pages"]:
                    break
                page += 1

    def proxy_url(self, work: dict, width: int) -> str | None:
        m = IMAGE_URL_RE.search(work.get("image_url") or "")
        if not m:
            return None
        return f"/api/img/aic/{m.group(1)}?w={width}"

    def fetch_image_bytes(self, image_id: str, width: int) -> tuple[bytes, str]:
        if not IMAGE_ID_RE.match(image_id) or width not in ALLOWED_WIDTHS:
            raise ImageUnavailable(400, "지원하지 않는 이미지 요청입니다.")
        req = urllib.request.Request(
            f"{IIIF}/{image_id}/full/{width},/0/default.jpg",
            headers={"AIC-User-Agent": USER_AGENT_IMAGE, "User-Agent": USER_AGENT_IMAGE},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read(), "image/jpeg"
        except urllib.error.HTTPError as e:
            raise ImageUnavailable(404 if e.code == 404 else 502, "이미지를 불러오지 못했습니다.") from e
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            raise ImageUnavailable(502, "이미지를 불러오지 못했습니다.") from e
