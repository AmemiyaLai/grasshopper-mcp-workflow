"""
example_usage 範例函式測試

這些函式的目的是展示，測試只驗證「可執行」且不會拋出例外。
MMD 解析與組件 API 均以 stub 取代，避免依賴真實檔案與 socket。
"""

import pytest

import grasshopper_tools.example_usage as eu
from grasshopper_tools.parser_utils import MMDParser, JSONGenerator
from grasshopper_tools.component_manager import ComponentManager


def test_example_basic_usage(monkeypatch, capsys):
    """add_component 失敗時走 else 分支，不拋出例外"""
    class FakeMM:
        def __init__(self, *a, **k):
            pass

        def add_component(self, *a, **k):
            return None

    monkeypatch.setattr(eu, "ComponentManager", FakeMM)
    eu.example_basic_usage()
    out = capsys.readouterr().out
    assert "基本使用範例" in out


def test_example_parse_mmd(monkeypatch, capsys):
    def fake_parse_empty(*a, **k):
        return ([{"componentId": "SLIDER_WIDTH", "guid": "g", "x": 1, "y": 2}], [{}])

    monkeypatch.setattr(MMDParser, "parse_component_info_mmd", fake_parse_empty)
    monkeypatch.setattr(MMDParser, "parse_subgraphs_from_mmd", lambda self, p: {"SG1": ["A", "B"]})
    monkeypatch.setattr(MMDParser, "get_subgraph_names", lambda self, p: {"SG1": "群組1"})
    monkeypatch.setattr(
        MMDParser,
        "parse_slider_values",
        lambda self, p: {"SLIDER_WIDTH": {"value": "120.0"}},
    )
    eu.example_parse_mmd()
    out = capsys.readouterr().out
    assert "解析 MMD 文件範例" in out
    assert "找到 1 個組件" in out
    assert "SLIDER_WIDTH: 120.0" in out


def test_example_parse_mmd_missing_file(monkeypatch, capsys):
    """檔案不存在時回傳提示並返回"""
    monkeypatch.setattr(eu.os.path, "exists", lambda p: False)
    eu.example_parse_mmd()
    assert "找不到文件" in capsys.readouterr().out


def test_example_generate_json(monkeypatch, capsys):
    def fake_parse(*a, **k):
        return (
            [{"componentId": "SLIDER_WIDTH", "guid": "g", "x": 1, "y": 2}],
            [{"sourceId": "s", "sourceParam": "P", "targetId": "t", "targetParam": "Q"}],
        )

    monkeypatch.setattr(MMDParser, "parse_component_info_mmd", fake_parse)
    saved = []
    monkeypatch.setattr(JSONGenerator, "save_placement_info", lambda self, info, path: saved.append((info, path)))
    eu.example_generate_json()
    out = capsys.readouterr().out
    assert "生成 JSON 文件範例" in out
    assert "已生成 8 個命令" in out
    assert saved and saved[0][0]["description"].startswith("桌子創建")


def test_example_generate_json_missing_file(monkeypatch, capsys):
    monkeypatch.setattr(eu.os.path, "exists", lambda p: False)
    eu.example_generate_json()
    assert "找不到文件" in capsys.readouterr().out


def test_example_full_workflow(monkeypatch, capsys):
    def fake_parse(*a, **k):
        return (
            [
                {"guid": "g1", "x": 1, "y": 2, "componentId": "A"},
                {"guid": "g2", "x": 3, "y": 4, "componentId": "B"},
                {"guid": "g3", "x": 5, "y": 6, "componentId": "C"},
            ],
            [],
        )

    monkeypatch.setattr(MMDParser, "parse_component_info_mmd", fake_parse)
    monkeypatch.setattr(eu.ComponentManager, "add_components_parallel", lambda self, cmds, max_workers=10: (0, 3))
    monkeypatch.setattr(eu.ComponentManager, "save_id_map", lambda self, *a, **k: None)

    eu.example_full_workflow()
    out = capsys.readouterr().out
    assert "完整工作流程範例" in out
    assert "成功: 0, 失敗: 3" in out


def test_example_full_workflow_missing_file(monkeypatch, capsys):
    monkeypatch.setattr(eu.os.path, "exists", lambda p: False)
    eu.example_full_workflow()
    assert "找不到文件" in capsys.readouterr().out


def test_example_full_workflow_exception(monkeypatch, capsys):
    def fake_parse(*a, **k):
        raise RuntimeError("伺服器未運行")

    monkeypatch.setattr(MMDParser, "parse_component_info_mmd", fake_parse)
    eu.example_full_workflow()
    out = capsys.readouterr().out
    assert "錯誤: 伺服器未運行" in out