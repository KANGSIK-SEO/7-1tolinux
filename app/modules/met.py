"""MET 드라이버: Metropolitan Museum of Art Open Access API에서 유럽 회화(부서 11) 중
퍼블릭 도메인 + 이미지 있는 작품을 가져온다. API 키 불필요. 이미지는 전용 헤더가 필요 없어
프록시 없이 원본 URL을 그대로 쓴다(proxy_url을 오버라이드하지 않음).
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterator

from ..kernel.base import ArtworkRecord, SourceModule

BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
SEARCH_BASE = "https://collectionapi.metmuseum.org/public/collection/v1.1"
DEPARTMENT_ID = 11  # European Paintings
SEARCH_PAGE_SIZE = 500  # v1.1/search 최대 limit
USER_AGENT = "7-1tolinux met-module"


def _get_json(url: str, params: dict | None = None, retries: int = 4, timeout: int = 30):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
        time.sleep(2 ** attempt)


def _to_record(o: dict) -> ArtworkRecord | None:
    if not o.get("isPublicDomain") or not o.get("primaryImage") or not o.get("title"):
        return None
    tags = [t["term"] for t in (o.get("tags") or []) if t.get("term")]
    source_url = (o.get("objectURL") or f"https://metmuseum.org/art/collection/search/{o['objectID']}")
    # MET이 www 서브도메인을 폐기해 API가 돌려주는 objectURL도 www 그대로라 깨짐 → apex 도메인으로 교정
    source_url = source_url.replace("https://www.metmuseum.org", "https://metmuseum.org")
    return ArtworkRecord(
        source="met",
        source_id=str(o["objectID"]),
        title=o["title"],
        image_url=o["primaryImage"],
        source_url=source_url,
        artist=o.get("artistDisplayName") or None,
        artist_bio=o.get("artistDisplayBio") or None,
        date_display=o.get("objectDate") or None,
        year_start=o.get("objectBeginDate"),
        year_end=o.get("objectEndDate"),
        medium=o.get("medium") or None,
        classification=o.get("classification") or o.get("objectName") or None,
        department=o.get("department") or None,
        origin=o.get("culture") or o.get("artistNationality") or None,
        style=o.get("period") or None,
        subjects=", ".join(tags) or None,
        thumbnail_url=o.get("primaryImageSmall") or None,
        credit_line=o.get("creditLine") or None,
        is_highlight=bool(o.get("isHighlight")),
    )


class MetModule(SourceModule):
    source = "met"

    def fetch_all(self, limit: int = 0) -> Iterator[ArtworkRecord]:
        ids: list[int] = []
        offset = 0
        while True:
            page = _get_json(f"{SEARCH_BASE}/search", {
                "departmentId": DEPARTMENT_ID, "isPublicDomain": "true", "hasImages": "true",
                "q": "*", "limit": SEARCH_PAGE_SIZE, "offset": offset,
            })
            page_ids = (page or {}).get("objectIDs") or []
            ids.extend(page_ids)
            total = (page or {}).get("total") or 0
            offset += SEARCH_PAGE_SIZE
            if not page_ids or offset >= total:
                break
        if limit:
            ids = ids[:limit]

        consecutive_403 = 0
        for obj_id in ids:
            time.sleep(0.5)  # WAF(레이트리밋) 회피용 완만한 스로틀, 단일 요청씩만 진행
            try:
                obj = _get_json(f"{BASE}/objects/{obj_id}", retries=1)
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    consecutive_403 += 1
                    cooldown = min(20 * consecutive_403, 180)
                    time.sleep(cooldown)
                continue
            except Exception:
                continue
            consecutive_403 = 0
            if obj is None:
                continue
            record = _to_record(obj)
            if record is not None:
                yield record
