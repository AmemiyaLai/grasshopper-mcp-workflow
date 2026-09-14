"""
通用工具函數測試
"""

import builtins
import json

import pytest

from grasshopper_tools import utils


def failing_open(real_open, paths):
    """包裝內建 open，對指定路徑拋出 OSError，其餘照常"""
    def wrapper(*a, **k):
        target = a[0] if a else k.get("file")
        if target in paths:
            raise OSError("boom")
        return real_open(*a, **k)
    return wrapper


def test_load_component_id_map_default_missing(tmp_path, monkeypatch):
    """預設路徑檔不存在時回傳 None"""
    # 預設路徑基於 __file__，避免碰觸專案根目錄的真實 component_id_map.json，
    # 讓 dirname 指向 tmp 下的空目錄，使預設檔案路徑不存在
    monkeypatch.setattr(utils.os.path, "dirname", lambda p: str(tmp_path / "empty_dir"))
    assert utils.load_component_id_map() is None


def test_load_component_id_map_existing(tmp_path):
    path = tmp_path / "id_map.json"
    path.write_text(json.dumps({"A": "a"}), encoding="utf-8")
    assert utils.load_component_id_map(str(path)) == {"A": "a"}


def test_load_component_id_map_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{invalid", encoding="utf-8")
    assert utils.load_component_id_map(str(path)) is None


def test_load_component_id_map_read_error(tmp_path, monkeypatch):
    path = tmp_path / "x.json"
    path.write_text('{"A": "a"}', encoding="utf-8")
    monkeypatch.setattr(builtins, "open", failing_open(builtins.open, {str(path)}))
    assert utils.load_component_id_map(str(path)) is None


def test_save_component_id_map(tmp_path):
    path = tmp_path / "saved.json"
    utils.save_component_id_map({"A": "a", "B": "b"}, str(path))
    assert json.loads(path.read_text(encoding="utf-8")) == {"A": "a", "B": "b"}


def test_save_component_id_map_error(tmp_path, monkeypatch):
    target = str(tmp_path / "x.json")
    monkeypatch.setattr(builtins, "open", failing_open(builtins.open, {target}))
    utils.save_component_id_map({"A": "a"}, target)  # 不應拋出


def test_hex_to_rgb_with_hash():
    assert utils.hex_to_rgb("#FF0000") == (255, 0, 0)


def test_hex_to_rgb_without_hash():
    assert utils.hex_to_rgb("00FF80") == (0, 255, 128)


@pytest.mark.parametrize(
    "name,value,expected",
    [
        ("SLIDER_WIDTH", 50.0, (0.0, 200.0)),
        ("SLIDER_LENGTH", 300.0, (0.0, 600.0)),
        ("SLIDER_TOP_HEIGHT", 150.0, (0.0, 300.0)),
        ("SLIDER_TOP_Z", 120.0, (0.0, 240.0)),
        ("SLIDER_RADIUS_LEG", 30.0, (0.0, 60.0)),
        ("SLIDER_RADIUS_LEG", 10.0, (0.0, 50.0)),
        ("SLIDER_LEG1_X", 25.0, (-100.0, 100.0)),
        ("SLIDER_LEG1_Y", 25.0, (-100.0, 100.0)),
        ("SLIDER_LEG1_Z", 25.0, (-100.0, 100.0)),
        ("CONSTANT_2", 8.0, (0.0, 10.0)),
        ("UNKNOWN_SLIDER", 10.0, (0.0, 200.0)),
    ],
)
def test_determine_slider_range(name, value, expected):
    assert utils.determine_slider_range(name, value) == expected


def test_load_placement_info_success(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"commands": []}), encoding="utf-8")
    assert utils.load_placement_info(str(path)) == {"commands": []}


def test_load_placement_info_not_found(tmp_path, capsys):
    assert utils.load_placement_info(str(tmp_path / "nope.json")) is None
    assert "找不到文件" in capsys.readouterr().out


def test_load_placement_info_json_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{nope", encoding="utf-8")
    assert utils.load_placement_info(str(path)) is None


def test_load_placement_info_other_error(tmp_path, monkeypatch):
    path = tmp_path / "ok.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(builtins, "open", failing_open(builtins.open, {str(path)}))
    assert utils.load_placement_info(str(path)) is None


def build_placement_json(tmp_path, commands):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"commands": commands}, ensure_ascii=False), encoding="utf-8")
    return path


def test_update_guids_in_json_success(tmp_path):
    guid_map = {"old-guid": "new-guid"}
    path = build_placement_json(
        tmp_path,
        [
            {
                "type": "add_component",
                "parameters": {"guid": "old-guid"},
                "comment": "測試",
            },
            {
                "type": "add_component",
                "parameters": {"guid": "other-guid"},
                "comment": "其他",
            },
            {"type": "connect_components", "parameters": {}},
        ],
    )
    count = utils.update_guids_in_json(str(path), guid_map)
    assert count == 1
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["commands"][0]["parameters"]["guid"] == "new-guid"
    assert data["commands"][1]["parameters"]["guid"] == "other-guid"


def test_update_guids_in_json_read_error(tmp_path, monkeypatch):
    target = str(tmp_path / "x.json")
    monkeypatch.setattr(builtins, "open", failing_open(builtins.open, {target}))
    assert utils.update_guids_in_json(target, {}) == 0


def test_update_guids_in_json_write_error(tmp_path, monkeypatch):
    path = build_placement_json(tmp_path, [])
    real_open = builtins.open

    def flaky_open(*a, **k):
        if "w" in str(k.get("mode", "")) or (a and "w" in str(a[1])):
            raise OSError("write fail")
        return real_open(*a, **k)

    monkeypatch.setattr(builtins, "open", flaky_open)
    assert utils.update_guids_in_json(str(path), {}) == 0


def test_update_guids_in_json_no_match(tmp_path, capsys):
    path = build_placement_json(tmp_path, [{"type": "add_component", "parameters": {"guid": "other"}}])
    assert utils.update_guids_in_json(str(path), {"a": "b"}) == 0
    assert "總共更新了 0" in capsys.readouterr().out


def test_default_guid_map_present():
    assert len(utils.DEFAULT_GUID_MAP) == 12
    assert "6301d658-592f-47d0-ae0d-ad3c183a7ea5" in utils.DEFAULT_GUID_MAP