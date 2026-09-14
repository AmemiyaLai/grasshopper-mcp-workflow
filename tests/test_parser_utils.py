"""
MMD/JSON 解析工具測試
"""

import json

import pytest

from grasshopper_tools.parser_utils import MMDParser, JSONGenerator


def test_parse_component_info_mmd_basic(sample_mmd):
    parser = MMDParser()
    components, connections = parser.parse_component_info_mmd(str(sample_mmd))

    # SLIDER_WIDTH、DIVISION_X、CIRCLE_LEG_BASE 三個組件
    assert len(components) == 3
    ids = {c["componentId"] for c in components}
    assert ids == {"SLIDER_WIDTH", "DIVISION_X", "CIRCLE_LEG_BASE"}

    slider = next(c for c in components if c["componentId"] == "SLIDER_WIDTH")
    assert slider["guid"] == "e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da"
    assert slider["x"] == 100
    assert slider["y"] == 50

    # 兩條連接（SLIDER_WIDTH -> DIVISION_X、SLIDER_WIDTH -> CIRCLE_LEG_BASE）
    assert len(connections) == 2
    conn = connections[0]
    assert conn["sourceId"] == "SLIDER_WIDTH"
    assert conn["targetId"] == "DIVISION_X"
    assert conn["sourceParam"] == "Number"
    # DIVISION_X 且來源為 SLIDER → targetParam = A
    assert conn["targetParam"] == "A"


def test_parse_component_info_mmd_with_reference_guid(tmp_path):
    """GUID 為「需要查詢實際GUID」時應自 guid_map 替換"""
    content = (
        "SLIDER_WIDTH[\"Number Slider<br/>GUID: 需要查詢實際GUID<br/>位置: X=10, Y=20\"]"
    )
    path = tmp_path / "r.mmd"
    path.write_text(content, encoding="utf-8")
    components, _ = MMDParser().parse_component_info_mmd(str(path))
    assert components[0]["guid"] == MMDParser().guid_map["SLIDER_WIDTH"]


def test_parse_component_info_mmd_missing_guid(tmp_path, capsys):
    """組件沒有 GUID 資訊且不在 guid_map 中 → 警告並跳過"""
    content = 'UNKNOWN_COMP["Some Component<br/>位置: X=10, Y=20"]'
    path = tmp_path / "m.mmd"
    path.write_text(content, encoding="utf-8")
    components, _ = MMDParser().parse_component_info_mmd(str(path))
    assert components == []
    assert "未找到 GUID" in capsys.readouterr().out


def test_parse_component_info_mmd_missing_position(tmp_path, capsys):
    """組件缺少位置資訊 → 警告並跳過"""
    content = 'SLIDER_WIDTH["Number Slider<br/>GUID: e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da"]'
    path = tmp_path / "p.mmd"
    path.write_text(content, encoding="utf-8")
    components, _ = MMDParser().parse_component_info_mmd(str(path))
    assert components == []
    assert "未找到位置信息" in capsys.readouterr().out


def test_parse_component_info_mmd_unknown_guid_kept(tmp_path):
    """GUID 為一般格式但不在 guid_map 中時保留原值"""
    content = 'CUSTOM["Foo<br/>GUID: abc-def-123<br/>位置: X=10, Y=20"]'
    path = tmp_path / "u.mmd"
    path.write_text(content, encoding="utf-8")
    components, _ = MMDParser().parse_component_info_mmd(str(path))
    assert components[0]["guid"] == "abc-def-123"


def test_determine_params_math_parts():
    parser = MMDParser()
    assert parser._determine_params("SLIDER_A", "AVERAGE_LEG_X", "Number") == ("Number", "Input")
    assert parser._determine_params("SLIDER_WIDTH", "DIVISION_X", "Number") == ("Number", "A")
    assert parser._determine_params("CONSTANT_2", "DIVISION_Y", "Number") == ("Number", "B")
    assert parser._determine_params("OTHER", "PLAIN", "Number") == ("Number", "Number")


def test_determine_params_planes_and_vectors():
    parser = MMDParser()
    assert parser._determine_params("XY_PLANE", "CIRCLE_X", "Plane") == ("Plane", "Plane")
    assert parser._determine_params("XY_PLANE", "CENTER_BOX", "Plane") == ("Plane", "Base")
    assert parser._determine_params("XYZ", "PLAIN", "Plane") == ("Plane", "Plane")
    assert parser._determine_params("VECTOR", "MOVE_X", "Vector") == ("Vector", "Motion")
    assert parser._determine_params("VECTOR", "EXTRUDE_X", "Vector") == ("Vector", "Direction")
    assert parser._determine_params("VECTOR", "PLAIN", "Vector") == ("Vector", "Vector")


def test_determine_params_division_output():
    parser = MMDParser()
    assert parser._determine_params("DIVISION_X", "CENTER_BOX_TOP", "Number") == ("Result", "X")
    assert parser._determine_params("DIVISION_Y", "CENTER_BOX_TOP", "Number") == ("Result", "Y")
    assert parser._determine_params("DIVISION_Z", "CENTER_BOX_TOP", "Number") == ("Result", "Z")


def test_determine_params_circle_input():
    parser = MMDParser()
    assert parser._determine_params("XY_PLANE_LEG_BASE", "CIRCLE_LEG_BASE", "Plane") == ("Plane", "Plane")
    assert parser._determine_params("SLIDER_RADIUS_LEG", "CIRCLE_LEG_BASE", "Number") == ("Number", "Radius")


def test_parse_subgraphs_from_mmd(sample_mmd):
    parser = MMDParser()
    subgraphs = parser.parse_subgraphs_from_mmd(str(sample_mmd))
    assert set(subgraphs.keys()) == {"TOP", "LEG_BASE"}
    assert subgraphs["TOP"] == ["SLIDER_WIDTH", "DIVISION_X"]
    assert subgraphs["LEG_BASE"] == ["CIRCLE_LEG_BASE"]


def test_parse_subgraphs_nested_and_end(sample_mmd):
    """測試 subgraph 結束後進入下一層、以及最後無組件的情況"""
    content = """```mermaid
flowchart TD
    subgraph A["A 群組"]
        X["X<br/>GUID: a<br/>位置: X=1, Y=2"]
    end
    subgraph B["B 群組"]
        Y["Y<br/>GUID: b<br/>位置: X=3, Y=4"]
    end
end
```
"""
    path = sample_mmd.parent / "nested.mmd"
    path.write_text(content, encoding="utf-8")
    subgraphs = MMDParser().parse_subgraphs_from_mmd(str(path))
    assert subgraphs == {"A": ["X"], "B": ["Y"]}


def test_get_subgraph_names(sample_mmd):
    names = MMDParser().get_subgraph_names(str(sample_mmd))
    assert names == {"TOP": "桌面模組", "LEG_BASE": "桌腳基礎模組"}


def test_parse_slider_values(sample_mmd):
    parser = MMDParser()
    sliders = parser.parse_slider_values(str(sample_mmd))
    assert "SLIDER_WIDTH" in sliders
    assert sliders["SLIDER_WIDTH"]["type"] == "Number Slider"
    assert sliders["SLIDER_WIDTH"]["value"] == "120.0"
    # DIVISION_X 不是 Number Slider
    assert "DIVISION_X" not in sliders


def test_parse_slider_values_negative(tmp_path):
    content = 'S1["Number Slider<br/>输出: -12.5<br/>位置: X=1, Y=2"]'
    path = tmp_path / "s.mmd"
    path.write_text(content, encoding="utf-8")
    sliders = MMDParser().parse_slider_values(str(path))
    assert sliders["S1"]["value"] == "-12.5"


def test_generate_placement_info(sample_mmd):
    parser = MMDParser()
    components, connections = parser.parse_component_info_mmd(str(sample_mmd))
    info = JSONGenerator.generate_placement_info(components, connections, description="測試")

    assert info["description"] == "測試"
    commands = info["commands"]
    add_commands = [c for c in commands if c.get("type") == "add_component"]
    connect_commands = [c for c in commands if c.get("type") == "connect_components"]

    # 3 個組件全部在模組列表中
    assert len(add_commands) == 3
    # 2 條連接
    assert len(connect_commands) == 2

    # 驗證桌面模組組件順序與 comment
    assert add_commands[0]["comment"] == "SLIDER_WIDTH"
    assert add_commands[0]["parameters"]["guid"] == "e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da"


def test_generate_placement_info_skips_unknown_components():
    """componentId 不在已知模組清單中的組件不會被加入"""
    components = [{"componentId": "MYSTERY_COMP", "guid": "g", "x": 1, "y": 2}]
    info = JSONGenerator.generate_placement_info(components, [], description="x")
    add_commands = [c for c in info["commands"] if c.get("type") == "add_component"]
    assert add_commands == []


def test_save_placement_info(tmp_path, sample_mmd):
    parser = MMDParser()
    components, connections = parser.parse_component_info_mmd(str(sample_mmd))
    info = JSONGenerator.generate_placement_info(components, connections)
    out = tmp_path / "out.json"
    JSONGenerator.save_placement_info(info, str(out))
    assert json.loads(out.read_text(encoding="utf-8"))["description"] == "自動生成"