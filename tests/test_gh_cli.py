"""
gh_cli 快捷腳本測試

gh_cli 的程式碼在主檔守衛內執行，透過 exec 模擬 __main__ 執行環境。
"""

import sys
from pathlib import Path

import pytest


def test_gh_cli_import():
    """模組匯入即可（路徑設定等程式碼）"""
    import grasshopper_tools.gh_cli  # noqa: F401


def test_gh_cli_main_entry(monkeypatch):
    """以 __main__ 執行時會呼叫 cli.main()"""
    import grasshopper_tools.gh_cli as gh

    ran = []

    class PseudoMain:
        def __init__(self, *args, **kwargs):
            pass

    # 取代 cli.main，讓 exec 時不會真的執行 argparse
    monkeypatch.setattr("grasshopper_tools.cli.main", lambda: ran.append(1))

    source = Path(gh.__file__).read_text(encoding="utf-8")
    g = {"__name__": "__main__", "__file__": str(gh.__file__)}
    exec(compile(source, str(gh.__file__), "exec"), g)
    assert ran == [1]