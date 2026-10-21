"""命令行入口：``osls install`` / ``osls uninstall`` / ``osls status``。"""

from __future__ import annotations

import argparse
import sys

from . import installer


def _cmd_status(_: argparse.Namespace) -> int:
    info = installer.status()
    print("OpenSquilla 目录 :", info["opensquilla_dir"])
    print("通道文件        :", info["channel_file"])
    print("OpenSquilla 版本 :", info["opensquilla_version"])
    print("插件版本        :", info["plugin_version"])
    print("安装状态        :", "已注入" if info["installed"] else "未注入")
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    backup = installer.install()
    print("已注入流式卡片 shim")
    print("备份文件:", backup)
    print("重启 gateway 后生效：systemctl --user restart opensquilla-gateway")
    return 0


def _cmd_uninstall(_: argparse.Namespace) -> int:
    changed = installer.uninstall()
    print("已移除 shim" if changed else "未检测到 shim，无需处理")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="osls", description="OpenSquilla 飞书流式卡片安装器"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    install_parser = sub.add_parser("install", help="把 shim 注入 OpenSquilla 的 Feishu 通道")
    install_parser.set_defaults(func=_cmd_install)

    uninstall_parser = sub.add_parser("uninstall", help="移除 shim")
    uninstall_parser.set_defaults(func=_cmd_uninstall)

    status_parser = sub.add_parser("status", help="查看安装状态")
    status_parser.set_defaults(func=_cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI 要给出人话错误
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
