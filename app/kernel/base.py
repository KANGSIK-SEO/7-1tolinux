"""7-1tolinux 커널의 고정 계약.

art_linux(artlinux.kernel.VerificationModule)와 같은 철학: 커널은 "미술관 출처 하나를
어떻게 다뤄야 하는가"에 대한 안정된 인터페이스만 들고 있고, 실제 수집·이미지 접근 로직은
전부 modules/ 쪽 드라이버가 구현한다. 커널 쪽 코드는 특정 미술관을 몰라야 한다.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class ArtworkRecord:
    """모든 소스 모듈이 공통으로 맞춰야 하는 정규화된 작품 레코드. db/schema.sql의 artworks와 1:1."""

    source: str                     # 모듈 고유 슬러그 (예: "met", "aic"). SourceModule.source와 같아야 한다.
    source_id: str
    title: str
    image_url: str
    source_url: str
    artist: str | None = None
    artist_bio: str | None = None
    date_display: str | None = None
    year_start: int | None = None
    year_end: int | None = None
    medium: str | None = None
    classification: str | None = None
    department: str | None = None
    origin: str | None = None
    style: str | None = None
    subjects: str | None = None
    thumbnail_url: str | None = None
    credit_line: str | None = None
    is_public_domain: bool = True
    license: str = "CC0"
    is_highlight: bool = False


class ImageUnavailable(Exception):
    """이미지 프록시 호출이 실패했을 때. status는 그대로 API 응답 코드로 쓰인다."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class SourceModule(ABC):
    """미술관 출처 하나를 대표하는 드라이버. `sevenonelinux.modules` entry-point로 등록한다."""

    source: str  # artworks.source 컬럼 값. 모듈마다 고유해야 한다.

    @abstractmethod
    def fetch_all(self, limit: int = 0) -> Iterator[ArtworkRecord]:
        """해당 출처의 퍼블릭 도메인 작품을 ArtworkRecord로 yield한다. limit=0이면 전체."""
        raise NotImplementedError

    def proxy_url(self, work: dict, width: int) -> str | None:
        """이 소스의 이미지가 전용 헤더 등 특별 취급이 필요하면 `/api/img/<source>/<id>` 경로를
        돌려주고, 원본 URL을 그대로 써도 되면 None을 돌려준다(기본값)."""
        return None

    def fetch_image_bytes(self, image_id: str, width: int) -> tuple[bytes, str]:
        """proxy_url이 가리키는 경로가 호출하는 실제 이미지 페치. (bytes, content_type)을 돌려준다.
        이 모듈이 프록시를 쓰지 않는다면 구현하지 않아도 된다."""
        raise NotImplementedError(f"{self.source} 모듈은 이미지 프록시를 지원하지 않습니다.")
