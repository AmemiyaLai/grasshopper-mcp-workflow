"""
群組管理器測試
"""

from grasshopper_tools.group_manager import GroupManager
from grasshopper_tools.component_manager import ComponentManager


def test_group_components_success_with_ids(client):
    mgr = GroupManager(client)
    client.set_response(
        "group_components",
        {"success": True, "data": {"success": True}},
    )
    assert mgr.group_components(["id-1", "id-2"], "群組", (10, 20, 30)) is True
    params = client.commands[0][1]
    assert params == {
        "componentIds": ["id-1", "id-2"],
        "groupName": "群組",
        "colorR": 10,
        "colorG": 20,
        "colorB": 30,
    }


def test_group_components_with_color_hex(client):
    mgr = GroupManager(client)
    client.set_response("group_components", {"success": True, "data": {"success": True}})
    assert mgr.group_components(["id"], "g", color_hex="#FF0000") is True
    params = client.commands[0][1]
    assert (params["colorR"], params["colorG"], params["colorB"]) == (255, 0, 0)


def test_group_components_default_color(client):
    mgr = GroupManager(client)
    client.set_response("group_components", {"success": True, "data": {"success": True}})
    assert mgr.group_components(["id"], "g") is True
    params = client.commands[0][1]
    assert params["colorR"] == 200
    assert params["colorG"] == 200
    assert params["colorB"] == 200


def test_group_components_with_id_keys(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"K1": "real-1", "K2": "real-2", "K3": "real-3"}
    mgr = GroupManager(client, comp_mgr)
    client.set_response("group_components", {"success": True, "data": {"success": True}})
    assert mgr.group_components([], "g", component_id_keys=["K1", "K2", "K3"]) is True
    assert client.commands[0][1]["componentIds"] == ["real-1", "real-2", "real-3"]


def test_group_components_with_missing_keys(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"K1": "real-1"}
    mgr = GroupManager(client, comp_mgr)
    client.set_response("group_components", {"success": True, "data": {"success": True}})

    assert mgr.group_components([], "g", component_id_keys=["K1", "K2", "K3", "K4", "K5", "K6", "K7"]) is True
    assert any("警告: 群組中有" in str(c) for c in client.print_calls)
    assert any("... 還有" in str(c) for c in client.print_calls)


def test_group_components_missing_under_five(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"K1": "r1"}
    mgr = GroupManager(client, comp_mgr)
    client.set_response("group_components", {"success": True, "data": {"success": True}})
    assert mgr.group_components([], "g", component_id_keys=["K1", "K2"]) is True


def test_group_components_no_ids(client):
    mgr = GroupManager(client)
    assert mgr.group_components([], "g") is False
    assert any("錯誤: 沒有可用的組件 ID" in str(c) for c in client.print_calls)


def test_group_components_failure(client):
    mgr = GroupManager(client)
    client.set_response("group_components", {"success": False, "error": "no"})
    assert mgr.group_components(["id"], "g") is False
    assert any("群組失敗: no" in str(c) for c in client.print_calls)


def test_group_components_data_error_field(client):
    """回應 success=True 但 data.success=False 的情況"""
    mgr = GroupManager(client)
    client.set_response(
        "group_components",
        {"success": True, "data": {"success": False, "error": "data-err"}},
    )
    assert mgr.group_components(["id"], "g") is False
    assert any("群組失敗: data-err" in str(c) for c in client.print_calls)


def test_group_components_batch_success(client):
    client.set_response("group_components", {"success": True, "data": {"success": True}})
    mgr = GroupManager(client)
    groups = [
        {"name": "G1", "componentIds": ["a", "b"]},
        {"name": "G2", "componentIds": ["c"], "color": (1, 2, 3)},
        {"name": "G3", "componentIds": ["d"], "colorHex": "#00FF00"},
    ]
    success, fail = mgr.group_components_batch(groups)
    assert (success, fail) == (3, 0)


def test_group_components_batch_component_id_keys(client):
    """componentIdKeys 應傳入 group_components 的 component_id_keys"""
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"A": "real-a"}
    client.set_response("group_components", {"success": True, "data": {"success": True}})
    mgr = GroupManager(client, comp_mgr)
    groups = [{"name": "G", "componentIds": [], "componentIdKeys": ["A", "MISSING"]}]
    # MISSING 導致 key 查找失敗但仍有 real-a → 會成功
    success, fail = mgr.group_components_batch(groups)
    assert (success, fail) == (1, 0)


def test_group_components_batch_empty(client):
    mgr = GroupManager(client)
    success, fail = mgr.group_components_batch([])
    assert (success, fail) == (0, 0)