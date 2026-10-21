"""安装器：把一段 shim 写进 OpenSquilla 的 Feishu 通道文件。

为什么用 shim 而不是整段改源码？

* 卡片逻辑全部留在本包里（可单测、可升级），site-packages 里只多 6 行；
* ``osls uninstall`` 能把文件干净还原；
* OpenSquilla 升级覆盖文件后，重跑一次 ``osls install`` 即可恢复。
"""

from __future__ import annotations

import importlib.util
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

SHIM_BEGIN = "# >>> opensquilla-lark-streaming shim (managed) >>>"
SHIM_END = "# <<< opensquilla-lark-streaming shim <<<"

SHIM_BODY = f"""{SHIM_BEGIN}
try:
    from opensquilla_lark_streaming import patch as _osls_patch

    _osls_patch.apply(FeishuChannel)
except Exception as _osls_exc:  # pragma: no cover
    import logging as _osls_logging

    _osls_logging.getLogger(__name__).warning(
        "opensquilla-lark-streaming 注入失败: %s", _osls_exc
    )
{SHIM_END}
"""


@dataclass
class Target:
    """定位结果。"""

    package_dir: Path
    channel_file: Path
    version: str = "unknown"


def locate() -> Target:
    """找到 OpenSquilla 的 channels/feishu.py。"""
    spec = importlib.util.find_spec("opensquilla")
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError("没有找到已安装的 opensquilla（先装 OpenSquilla 再装本插件）")
    package_dir = Path(list(spec.submodule_search_locations)[0])
    channel_file = package_dir / "channels" / "feishu.py"
    if not channel_file.exists():
        raise RuntimeError(f"OpenSquilla 结构不符，缺少 {channel_file}")
    version = "unknown"
    try:
        from importlib.metadata import version as dist_version

        version = dist_version("opensquilla")
    except Exception:  # noqa: BLE001
        pass
    return Target(package_dir=package_dir, channel_file=channel_file, version=version)


def _strip_shim(source: str) -> str:
    lines = source.splitlines(keepends=True)
    output: list[str] = []
    skipping = False
    for line in lines:
        if line.strip() == SHIM_BEGIN:
            skipping = True
            continue
        if line.strip() == SHIM_END:
            skipping = False
            continue
        if not skipping:
            output.append(line)
    return "".join(output).rstrip() + "\n"


def is_installed(target: Target) -> bool:
    return SHIM_BEGIN in target.channel_file.read_text(encoding="utf-8")


def install(*, python_executable: str | None = None) -> Path:
    """写入 shim；返回备份文件路径。"""
    target = locate()
    source = target.channel_file.read_text(encoding="utf-8")
    cleaned = _strip_shim(source)

    backup = target.channel_file.with_name(
        f"{target.channel_file.name}.bak-osls-{int(time.time())}"
    )
    shutil.copy2(target.channel_file, backup)

    target.channel_file.write_text(cleaned + "\n" + SHIM_BODY, encoding="utf-8")
    compile(target.channel_file.read_text(encoding="utf-8"), str(target.channel_file), "exec")
    return backup


def uninstall() -> bool:
    """去掉 shim（保留文件其余内容），返回是否有改动。"""
    target = locate()
    source = target.channel_file.read_text(encoding="utf-8")
    if SHIM_BEGIN not in source:
        return False
    target.channel_file.write_text(_strip_shim(source), encoding="utf-8")
    compile(target.channel_file.read_text(encoding="utf-8"), str(target.channel_file), "exec")
    return True


def status() -> dict[str, object]:
    """返回安装状态，供 CLI 打印。"""
    target = locate()
    installed = is_installed(target)
    try:
        from . import __version__ as package_version
    except Exception:  # noqa: BLE001
        package_version = "unknown"
    return {
        "opensquilla_dir": str(target.package_dir),
        "channel_file": str(target.channel_file),
        "opensquilla_version": target.version,
        "plugin_version": package_version,
        "installed": installed,
    }


__all__ = ["install", "uninstall", "status", "is_installed", "locate", "Target"]
