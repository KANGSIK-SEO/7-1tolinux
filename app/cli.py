"""7-1tolinux CLI — 커널 위에 꽂힌 드라이버를 들여다보고 돌리는 운영 도구.
`lsmod`/실행 느낌으로: `7-1tolinux modules`, `7-1tolinux collect [source] [--limit N]`.
"""
import argparse
import sys

from .collect import collect_source
from .kernel.registry import get_registry


def cmd_modules(_args) -> None:
    modules = get_registry().list()
    if not modules:
        print("설치된 모듈이 없습니다 (pyproject.toml의 [project.entry-points] 확인).")
        return
    for m in modules:
        cls = type(m)
        print(f"{m.source:10s} {cls.__module__}.{cls.__qualname__}")


def cmd_collect(args) -> None:
    registry = get_registry()
    if args.source:
        module = registry.get(args.source)
        if module is None:
            known = ", ".join(m.source for m in registry.list()) or "(없음)"
            print(f"알 수 없는 소스: {args.source!r} (설치된 모듈: {known})", file=sys.stderr)
            raise SystemExit(1)
        targets = [module]
    else:
        targets = registry.list()
    for module in targets:
        collect_source(module, limit=args.limit)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="7-1tolinux", description="미술관 출처를 모듈(드라이버)로 꽂는 커널 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_modules = sub.add_parser("modules", help="설치된 소스 모듈 나열 (lsmod)")
    p_modules.set_defaults(func=cmd_modules)

    p_collect = sub.add_parser("collect", help="모듈로 작품 데이터를 가져와 art.db에 반영")
    p_collect.add_argument("source", nargs="?", help="예: met, aic (생략하면 설치된 모듈 전체)")
    p_collect.add_argument("--limit", type=int, default=0, help="0이면 전체 수집")
    p_collect.set_defaults(func=cmd_collect)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
