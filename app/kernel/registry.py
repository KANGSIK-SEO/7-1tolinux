"""모듈 자동 탐색. Python entry-point 그룹(`sevenonelinux.modules`)에 등록된 SourceModule을
설치 시점에 자동으로 찾아 로드한다 — apt로 깐 드라이버를 커널이 lsmod로 보는 것과 같은 방식.
남이 새 미술관 모듈을 만들 때, 이 파일을 포함해 커널 쪽 코드는 한 줄도 건드릴 필요가 없다.
"""
from importlib.metadata import entry_points

from .base import SourceModule

GROUP = "sevenonelinux.modules"


class ModuleRegistry:
    def __init__(self):
        self._modules: dict[str, SourceModule] = {}
        self._load()

    def _load(self) -> None:
        for ep in entry_points(group=GROUP):
            module_cls = ep.load()
            instance = module_cls()
            if not isinstance(instance, SourceModule):
                raise TypeError(f"entry-point {ep.name!r}가 SourceModule을 상속하지 않습니다: {module_cls!r}")
            if instance.source in self._modules:
                raise ValueError(f"source 슬러그가 중복됩니다: {instance.source!r} ({ep.name})")
            self._modules[instance.source] = instance

    def list(self) -> list[SourceModule]:
        return list(self._modules.values())

    def get(self, source: str) -> SourceModule | None:
        return self._modules.get(source)


_registry: ModuleRegistry | None = None


def get_registry() -> ModuleRegistry:
    """프로세스당 한 번만 entry-point를 스캔한다."""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry


def reset_registry_for_tests() -> None:
    global _registry
    _registry = None
