"""
組件管理器測試
"""

from grasshopper_tools import component_manager as cm
from grasshopper_tools.component_manager import ComponentManager


def test_add_component_success_registers_map(client):
    mgr = ComponentManager(client)
    comp_id = mgr.add_component("guid-1", 100, 50, "SLIDER_WIDTH")
    assert comp_id == "gh-comp-id"
    assert mgr.component_id_map == {"SLIDER_WIDTH": "gh-comp-id"}
    assert client.commands[0][0] == "add_component"
    assert client.commands[0][1] == {"guid": "guid-1", "x": 100, "y": 50}


def test_add_component_success_without_component_id(client):
    mgr = ComponentManager(client)
    comp_id = mgr.add_component("guid-1", 1, 2)
    assert comp_id == "gh-comp-id"
    assert mgr.component_id_map == {}


def test_add_component_failure(client):
    client.set_response("add_component", {"success": False, "error": "失敗啦"})
    mgr = ComponentManager(client)
    assert mgr.add_component("guid-1", 1, 2, "SLIDER") is None
    assert mgr.component_id_map == {}
    assert any("創建組件失敗" in str(c) for c in client.print_calls)


def test_add_components_parallel_parameters_format(client):
    commands = [
        {
            "comment": "c1",
            "type": "add_component",
            "parameters": {"guid": "g1", "x": 1, "y": 2},
            "componentId": "ID_1",
        },
        {
            "comment": "c2",
            "type": "add_component",
            "parameters": {"guid": "g2", "x": 3, "y": 4},
            "componentId": "ID_2",
        },
    ]
    mgr = ComponentManager(client)
    success, fail = mgr.add_components_parallel(commands, max_workers=2)
    assert (success, fail) == (2, 0)
    assert mgr.component_id_map == {"ID_1": "gh-comp-id", "ID_2": "gh-comp-id"}


def test_add_components_parallel_direct_format(client):
    commands = [
        {"guid": "g1", "x": 5, "y": 6, "componentId": "D1"},
    ]
    mgr = ComponentManager(client)
    success, fail = mgr.add_components_parallel(commands)
    assert (success, fail) == (1, 0)


def test_add_components_parallel_missing_guid(client):
    commands = [
        {"x": 1, "y": 2},
        {"guid": "g2", "x": None, "y": 4},
        {"guid": "g3", "x": 3, "y": "not-a-number"},
    ]
    mgr = ComponentManager(client)
    success, fail = mgr.add_components_parallel(commands)
    assert (success, fail) == (0, 3)


def test_add_components_parallel_failure_response(client):
    client.set_response("add_component", {"success": False, "error": "no"})
    mgr = ComponentManager(client)
    success, fail = mgr.add_components_parallel([{"guid": "g", "x": 1, "y": 2}])
    assert (success, fail) == (0, 1)


def test_delete_component_success_removes_map(client):
    mgr = ComponentManager(client)
    mgr.component_id_map = {"SLIDER": "abc", "OTHER": "def"}
    client.set_response("delete_component", {"success": True})
    assert mgr.delete_component("abc") is True
    assert "abc" not in mgr.component_id_map.values()
    assert mgr.component_id_map == {"OTHER": "def"}


def test_delete_component_failure(client):
    client.set_response("delete_component", {"success": False, "error": "no"})
    mgr = ComponentManager(client)
    assert mgr.delete_component("abc") is False


def test_delete_component_ignores_unknown(client):
    """回應成功但組件不在映射中 → 不應報錯"""
    client.set_response("delete_component", {"success": True})
    mgr = ComponentManager(client)
    mgr.component_id_map = {"A": "id-a"}
    assert mgr.delete_component("id-x") is True
    assert mgr.component_id_map == {"A": "id-a"}


def test_set_component_visibility_via_map_key(client):
    mgr = ComponentManager(client)
    mgr.component_id_map = {"SLIDER": "real-id"}
    client.set_response("set_component_visibility", {"success": True})
    assert mgr.set_component_visibility("SLIDER", True) is True
    assert client.commands[-1][1] == {"componentId": "real-id", "hidden": True}


def test_set_component_visibility_direct_id(client):
    mgr = ComponentManager(client)
    client.set_response("set_component_visibility", {"success": True})
    assert mgr.set_component_visibility("direct-id", False) is True
    assert client.commands[-1][1] == {"componentId": "direct-id", "hidden": False}


def test_set_component_visibility_failure(client):
    client.set_response("set_component_visibility", {"success": False, "error": "no"})
    mgr = ComponentManager(client)
    assert mgr.set_component_visibility("x", True) is False


def test_zoom_to_components_mixed(client):
    mgr = ComponentManager(client)
    mgr.component_id_map = {"SLIDER": "real-id"}
    client.set_response("zoom_to_components", {"success": True})
    assert mgr.zoom_to_components(["SLIDER", "raw-id"]) is True
    assert client.commands[-1][1] == {"componentIds": ["real-id", "raw-id"]}


def test_zoom_to_components_failure(client):
    client.set_response("zoom_to_components", {"success": False, "error": "no"})
    mgr = ComponentManager(client)
    assert mgr.zoom_to_components(["a"]) is False


def test_get_component_guid_prefers_builtin(client):
    candidates = [
        {"name": "Nr", "guid": "g-old", "obsolete": True, "isBuiltIn": True, "category": "c1"},
        {"name": "Rectangle", "guid": "g-new", "obsolete": False, "isBuiltIn": True, "category": "c2"},
    ]
    client.set_response("get_component_candidates", {"success": True, "data": {"candidates": candidates}})
    mgr = ComponentManager(client)
    result = mgr.get_component_guid("Rectangle")
    assert result["guid"] == "g-new"
    assert result["isBuiltIn"] is True


def test_get_component_guid_fallback_non_obsolete(client):
    candidates = [
        {"name": "R", "guid": "g1", "obsolete": True, "isBuiltIn": True},
        {"name": "Rect", "guid": "g2", "obsolete": False, "isBuiltIn": False, "category": "c"},
    ]
    client.set_response("get_component_candidates", {"success": True, "result": {"candidates": candidates}})
    mgr = ComponentManager(client)
    result = mgr.get_component_guid("Rect")
    assert result["guid"] == "g2"
    assert result["isBuiltIn"] is False


def test_get_component_guid_last_resort_first_candidate(client):
    candidates = [{"name": "X", "guid": "g1", "obsolete": True, "isBuiltIn": False, "category": ""}]
    client.set_response("get_component_candidates", {"success": True, "data": {"candidates": candidates}})
    mgr = ComponentManager(client)
    result = mgr.get_component_guid("X")
    assert result["guid"] == "g1"


def test_get_component_guid_empty_candidates(client):
    client.set_response("get_component_candidates", {"success": True, "data": {"candidates": []}})
    mgr = ComponentManager(client)
    assert mgr.get_component_guid("X") is None


def test_get_component_guid_failure(client):
    client.set_response("get_component_candidates", {"success": False, "error": "no"})
    mgr = ComponentManager(client)
    assert mgr.get_component_guid("X") is None
    assert any("查詢 X 失敗" in str(c) for c in client.print_calls)


def test_get_component_id(client):
    mgr = ComponentManager(client)
    mgr.component_id_map = {"SLIDER": "id-1"}
    assert mgr.get_component_id("SLIDER") == "id-1"
    assert mgr.get_component_id("MISSING") is None


def test_save_id_map(client, monkeypatch):
    calls = {}

    def fake_save(mapping, path):
        calls["mapping"] = dict(mapping)
        calls["path"] = path

    monkeypatch.setattr(cm, "save_component_id_map", fake_save)
    mgr = ComponentManager(client)
    mgr.component_id_map = {"A": "a"}
    mgr.save_id_map("custom.json")
    assert calls["mapping"] == {"A": "a"}
    assert calls["path"] == "custom.json"


def test_save_id_map_default(client, monkeypatch):
    calls = {}

    def fake_save(mapping, path):
        calls["path"] = path

    monkeypatch.setattr(cm, "save_component_id_map", fake_save)
    mgr = ComponentManager(client)
    mgr.save_id_map()
    assert calls["path"] is None


def test_load_id_map(client, monkeypatch):
    def fake_load(path):
        return {"LOADED": "id"}

    monkeypatch.setattr("grasshopper_tools.utils.load_component_id_map", fake_load)
    mgr = ComponentManager(client)
    mgr.load_id_map("map.json")
    assert mgr.component_id_map == {"LOADED": "id"}


def test_load_id_map_no_file(client, monkeypatch):
    monkeypatch.setattr("grasshopper_tools.utils.load_component_id_map", lambda path: None)
    mgr = ComponentManager(client)
    mgr.load_id_map("missing.json")
    assert mgr.component_id_map == {}


def test_load_id_map_merge(client, monkeypatch):
    """已存在的映射應與載入內容合併，載入內容優先更新"""
    monkeypatch.setattr("grasshopper_tools.utils.load_component_id_map", lambda path: {"A": "new", "B": "b"})
    mgr = ComponentManager(client)
    mgr.component_id_map = {"A": "old", "C": "c"}
    mgr.load_id_map("map.json")
    assert mgr.component_id_map == {"A": "new", "B": "b", "C": "c"}