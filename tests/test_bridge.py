"""
grasshopper_mcp/bridge.py MCP 伺服器工具與資源測試

透過 monkeypatch 取代 socket 與 send_to_grasshopper，避免真實連線。
"""

import socket
import sys

import pytest

import grasshopper_mcp.bridge as bridge


class FakeSocket:
    """模擬 socket"""

    response = b'{"success": true}\n'
    fail_connect = False
    sent_data = b""

    def __init__(self, *args, **kwargs):
        pass

    def connect(self, addr):
        if FakeSocket.fail_connect:
            raise ConnectionError("模擬連線失敗")

    def sendall(self, data):
        FakeSocket.sent_data = data

    def recv(self, bufsize):
        r = FakeSocket.response
        FakeSocket.response = b""
        return r

    def close(self):
        pass


# ---------- send_to_grasshopper ----------

def test_send_command_success(monkeypatch):
    FakeSocket.response = b'{"success": true, "data": {"id": "x"}}\n'
    monkeypatch.setattr(socket, "socket", FakeSocket)
    resp = bridge.send_to_grasshopper("add_component", {"guid": "g", "x": 1, "y": 2})
    assert resp["success"] is True
    assert FakeSocket.sent_data == b'{"type": "add_component", "parameters": {"guid": "g", "x": 1, "y": 2}}\n'


def test_send_command_params_none(monkeypatch):
    FakeSocket.response = b'{"success": true}\n'
    monkeypatch.setattr(socket, "socket", FakeSocket)
    resp = bridge.send_to_grasshopper("clear_document")
    assert resp["success"] is True


def test_send_command_with_bom(monkeypatch):
    FakeSocket.response = '\ufeff{"success": true}\n'.encode("utf-8")
    monkeypatch.setattr(socket, "socket", FakeSocket)
    resp = bridge.send_to_grasshopper("get_document_info")
    assert resp["success"] is True


def test_send_command_multiple_recv(monkeypatch):
    chunks = iter([b'{"success": true}\n', b""])

    class MultiRecvSocket(FakeSocket):
        def recv(self, bufsize):
            return next(chunks)

    monkeypatch.setattr(socket, "socket", MultiRecvSocket)
    resp = bridge.send_to_grasshopper("get_connections")
    assert resp["success"] is True


def test_send_command_connection_error(monkeypatch):
    FakeSocket.fail_connect = True
    monkeypatch.setattr(socket, "socket", FakeSocket)
    resp = bridge.send_to_grasshopper("add_component")
    assert resp["success"] is False
    assert "Error communicating" in resp["error"]


def test_send_command_bad_json(monkeypatch):
    FakeSocket.response = b"not json"
    monkeypatch.setattr(socket, "socket", FakeSocket)
    resp = bridge.send_to_grasshopper("add_component")
    assert resp["success"] is False


# ---------- 工具函式的基本轉發 ----------

def make_recorder(monkeypatch):
    """取代 send_to_grasshopper，記錄呼叫並回傳成功回應"""
    calls = []

    def fake(command_type, params=None):
        calls.append((command_type, params or {}))
        return {"success": True, "data": {"id": "x"}, "result": {}}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    return calls


def test_add_component(monkeypatch):
    calls = make_recorder(monkeypatch)
    resp = bridge.add_component("guid-1", 100.0, 50.0)
    assert resp["success"]
    assert calls[0] == ("add_component", {"guid": "guid-1", "x": 100.0, "y": 50.0})


def test_add_component_without_guid(monkeypatch):
    make_recorder(monkeypatch)
    with pytest.raises(ValueError):
        bridge.add_component("", 1, 2)


def test_clear_document(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.clear_document()
    assert calls[0][0] == "clear_document"


def test_save_document(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.save_document("/tmp/test.gh")
    assert calls[0] == ("save_document", {"path": "/tmp/test.gh"})


def test_load_document(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.load_document("/tmp/test.gh")
    assert calls[0] == ("load_document", {"path": "/tmp/test.gh"})


def test_get_document_info(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.get_document_info()
    assert calls[0][0] == "get_document_info"


def test_create_pattern(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.create_pattern("3D voronoi cube")
    assert calls[0] == ("create_pattern", {"description": "3D voronoi cube"})


def test_get_available_patterns(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.get_available_patterns("voronoi")
    assert calls[0] == ("get_available_patterns", {"query": "voronoi"})


def test_get_document_errors(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.get_document_errors()
    assert calls[0][0] == "get_document_errors"


def test_get_connections(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.get_connections()
    assert calls[0][0] == "get_connections"


def test_search_components(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.search_components("rectangle")
    assert calls[0] == ("search_components", {"query": "rectangle"})


def test_get_component_parameters(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.get_component_parameters("Number Slider")
    assert calls[0] == ("get_component_parameters", {"componentType": "Number Slider"})


def test_get_component_candidates(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.get_component_candidates("Rectangle")
    assert calls[0] == ("get_component_candidates", {"name": "Rectangle"})


def test_validate_connection(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.validate_connection("s", "t", "P", "Q")
    params = calls[0][1]
    assert params["sourceId"] == "s" and params["targetId"] == "t"
    assert params["sourceParam"] == "P" and params["targetParam"] == "Q"


def test_validate_connection_minimal(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.validate_connection("s", "t")
    assert calls[0][1] == {"sourceId": "s", "targetId": "t"}


def test_set_slider_properties(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.set_slider_properties("id-1", value="10", min_value=0, max_value=100, rounding=0.1)
    params = calls[0][1]
    assert params["id"] == "id-1"
    assert params["component_type"] == "Number Slider"
    assert params["value"] == "10"
    assert params["min"] == 0 and params["max"] == 100 and params["rounding"] == 0.1


def test_set_slider_properties_minimal(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.set_slider_properties("id-1")
    params = calls[0][1]
    assert "value" not in params


def test_set_component_visibility(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.set_component_visibility("id-1", True)
    assert calls[0] == ("set_component_visibility", {"componentId": "id-1", "hidden": True})


# ---------- group_components ----------

def test_group_components_string_ids(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.group_components("a, b, c")
    assert calls[0][1]["componentIds"] == ["a", "b", "c"]


def test_group_components_list_ids(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.group_components(["x", "y"])
    assert calls[0][1]["componentIds"] == ["x", "y"]


def test_group_components_with_group_name_and_hex(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.group_components(["x"], group_name="G", color="#FF0000")
    params = calls[0][1]
    assert params["groupName"] == "G"
    assert params["color"] == "#FF0000"


def test_group_components_with_rgb(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.group_components(["x"], color_r=10, color_g=20, color_b=30)
    assert calls[0][1]["colorR"] == 10


def test_group_components_no_color(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.group_components(["x"])
    assert "color" not in calls[0][1]


# ---------- zoom_to_components ----------

def test_zoom_to_components_string(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.zoom_to_components("id1, id2")
    assert calls[0][1]["componentIds"] == ["id1", "id2"]


def test_zoom_to_components_list(monkeypatch):
    calls = make_recorder(monkeypatch)
    bridge.zoom_to_components(["id1", "id2"])
    assert calls[0][1]["componentIds"] == ["id1", "id2"]


def test_zoom_to_components_empty(monkeypatch):
    make_recorder(monkeypatch)
    with pytest.raises(ValueError):
        bridge.zoom_to_components("  ")


def test_zoom_to_components_empty_list(monkeypatch):
    make_recorder(monkeypatch)
    with pytest.raises(ValueError):
        bridge.zoom_to_components([""])


# ---------- connect_components 智能分配 ----------

def make_connect_sender(info_result, connections_result):
    """建立可記錄呼叫並依命令分派回應的 send_to_grasshopper"""
    calls = []

    def fake(command_type, params=None):
        params = params or {}
        calls.append((command_type, params))
        if command_type == "get_component_info":
            return info_result
        if command_type == "get_connections":
            return {"success": True, "result": connections_result}
        return {"success": True, "result": {}}

    fake.calls = calls
    return fake


def test_connect_components_plain(monkeypatch):
    sender = make_connect_sender(
        {"success": True, "result": {"type": "Panel"}}, []
    )
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt", "P", "Q")
    final = sender.calls[-1][1]
    assert final["sourceParam"] == "P" and final["targetParam"] == "Q"


def test_connect_components_addition_first_slot(monkeypatch):
    """Addition 且第一輸入未佔用 → target_param = A"""
    sender = make_connect_sender(
        {"success": True, "result": {"type": "Addition"}}, []
    )
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt")
    final = sender.calls[-1][1]
    assert final["targetParam"] == "A"


def test_connect_components_addition_second_slot(monkeypatch):
    """Addition 且第一輸入已被佔用 → target_param = B"""
    sender = make_connect_sender(
        {"success": True, "result": {"type": "Addition"}},
        [{"targetId": "tgt", "targetParam": "A"}],
    )
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt")
    final = sender.calls[-1][1]
    assert final["targetParam"] == "B"


def test_connect_components_amplitude_vector(monkeypatch):
    """Amplitude 且未佔用 → target_param = Vector"""
    sender = make_connect_sender(
        {"success": True, "result": {"type": "Amplitude"}}, []
    )
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt")
    assert sender.calls[-1][1]["targetParam"] == "Vector"


def test_connect_components_amplitude_amplitude(monkeypatch):
    """Amplitude 且已佔用（targetParamIndex=0 也算）→ target_param = Amplitude"""
    sender = make_connect_sender(
        {"success": True, "result": {"type": "Amplitude"}},
        [{"targetId": "tgt", "targetParamIndex": 0}],
    )
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt")
    assert sender.calls[-1][1]["targetParam"] == "Amplitude"


def test_connect_components_no_type_info(monkeypatch):
    """回傳沒有 result.type → 不做智能分配"""
    sender = make_connect_sender({"success": True, "result": {}}, [])
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt")
    final = sender.calls[-1][1]
    assert "targetParam" not in final


def test_connect_components_target_param_explicit(monkeypatch):
    """已明確指定 target_param → 維持原值"""
    sender = make_connect_sender(
        {"success": True, "result": {"type": "Addition"}}, []
    )
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt", target_param="Manual")
    assert sender.calls[-1][1]["targetParam"] == "Manual"


def test_connect_components_index_params(monkeypatch):
    """source_param_index / target_param_index → 轉為 sourceParamIndex / targetParamIndex"""
    sender = make_connect_sender({"success": True, "result": {"type": "Panel"}}, [])
    monkeypatch.setattr(bridge, "send_to_grasshopper", sender)
    bridge.connect_components("src", "tgt", source_param_index=1, target_param_index=2)
    final = sender.calls[-1][1]
    assert final["sourceParamIndex"] == 1
    assert final["targetParamIndex"] == 2


# ---------- get_component_info 增強 ----------

def test_get_component_info_enrichment(monkeypatch):
    """type 匹配組件庫時合併 settings/inputs/outputs 等資訊"""
    calls = []

    def fake(command_type, params=None):
        params = params or {}
        calls.append(command_type)
        if command_type == "get_component_info":
            return {"result": {"id": "c1", "type": "Addition"}}
        if command_type == "get_connections":
            return {"result": [{"sourceId": "s", "targetId": "c1"}]}
        return {"success": True, "result": {}}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    monkeypatch.setattr(
        bridge,
        "get_component_library",
        lambda: {
            "components": [
                {
                    "name": "Addition",
                    "fullName": "Addition",
                    "settings": {"operation": "+"},
                    "inputs": [{"name": "A"}, {"name": "B"}],
                    "outputs": [{"name": "Result"}],
                    "usage_examples": ["ex"],
                    "common_issues": ["issue"],
                }
            ]
        },
    )
    result = bridge.get_component_info("c1")
    data = result["result"]
    assert data["id"] == "c1"
    # Addition 在組件庫中 → 合併 inputDetails / outputDetails
    assert "inputDetails" in data
    assert "outputDetails" in data
    # 有相關連接 → 加入 connections
    assert data["connections"] == [{"sourceId": "s", "targetId": "c1"}]


def test_get_component_info_number_slider_settings(monkeypatch):
    """Number Slider 無 currentSettings 時自動補上"""
    def fake(command_type, params=None):
        if command_type == "get_component_info":
            return {"result": {"id": "sl", "type": "Number Slider", "value": 7}}
        if command_type == "get_connections":
            return {"result": []}
        return {"success": True, "result": {}}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    result = bridge.get_component_info("sl")
    cs = result["result"]["currentSettings"]
    assert cs["value"] == 7
    assert cs["min"] == 0 and cs["max"] == 10


def test_get_component_info_existing_settings(monkeypatch):
    """已有 currentSettings → 不覆寫"""
    def fake(command_type, params=None):
        if command_type == "get_component_info":
            return {"result": {"id": "sl", "type": "Number Slider", "currentSettings": {"value": 99}}}
        if command_type == "get_connections":
            return {"result": []}
        return {"success": True, "result": {}}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    result = bridge.get_component_info("sl")
    assert result["result"]["currentSettings"]["value"] == 99


def test_get_component_info_unknown_type(monkeypatch):
    """type 不在組件庫中 → 不回傳錯誤"""
    def fake(command_type, params=None):
        if command_type == "get_component_info":
            return {"result": {"id": "x", "type": "NoSuchComponent"}}
        if command_type == "get_connections":
            return {"result": []}
        return {"success": True, "result": {}}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    result = bridge.get_component_info("x")
    assert result["result"]["id"] == "x"


def test_get_component_info_no_result(monkeypatch):
    def fake(command_type, params=None):
        return {"success": False, "error": "no"}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    result = bridge.get_component_info("x")
    assert result["success"] is False


# ---------- get_all_components 增強 ----------

def test_get_all_components_enrichment(monkeypatch):
    calls = []

    def fake(command_type, params=None):
        params = params or {}
        calls.append(command_type)
        if command_type == "get_all_components":
            return {
                "result": [
                    {"id": "c1", "type": "Addition", "x": 0, "y": 0},
                    {"id": "sl", "type": "Number Slider", "x": 1, "y": 1},
                ]
            }
        if command_type == "get_connections":
            return {"result": [{"sourceId": "c1", "targetId": "sl"}]}
        if command_type == "get_component_info":
            return {"result": {"min": 0, "max": 5, "value": 2, "rounding": 0.1}}
        return {"success": True, "result": {}}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    monkeypatch.setattr(
        bridge,
        "get_component_library",
        lambda: {
            "components": [
                {
                    "name": "Addition",
                    "fullName": "Addition",
                    "settings": {},
                    "inputs": [{"name": "A"}, {"name": "B"}],
                    "outputs": [{"name": "Result"}],
                },
                {"name": "Number Slider", "fullName": "Number Slider", "inputs": [], "outputs": [{"name": "N"}]},
            ]
        },
    )
    result = bridge.get_all_components()
    components = result["result"]
    addition = next(c for c in components if c["id"] == "c1")
    slider = next(c for c in components if c["id"] == "sl")

    assert addition["inputDetails"]  # 組件庫合併
    assert addition["connections"] == [{"sourceId": "c1", "targetId": "sl"}]
    # Number Slider → 透過 get_component_info 取得 currentSettings
    assert slider["currentSettings"] == {"min": 0, "max": 5, "value": 2, "rounding": 0.1}


def test_get_all_components_no_result(monkeypatch):
    def fake(command_type, params=None):
        return {"success": False, "error": "no"}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)
    assert bridge.get_all_components()["success"] is False


# ---------- 資源 ----------

def test_get_grasshopper_status(monkeypatch):
    def fake(command_type, params=None):
        params = params or {}
        if command_type == "get_document_info":
            return {"result": {"name": "doc"}}
        if command_type == "get_connections":
            return {"result": [{"sourceId": "s", "targetId": "t", "sourceParam": "", "targetParam": ""}]}
        return {"success": True, "result": []}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)

    def fake_all():
        return {
            "result": [
                {"id": "c1", "type": "Number Slider", "x": 1, "y": 2, "currentSettings": {"value": 5}},
                {"id": "c2", "type": "Panel", "x": 3, "y": 4},
            ]
        }

    monkeypatch.setattr(bridge, "get_all_components", fake_all)
    status = bridge.get_grasshopper_status()
    assert status["status"] == "Connected to Grasshopper"
    assert status["document"] == {"name": "doc"}
    assert len(status["components"]) == 2
    assert status["components"][0]["settings"] == {"value": 5}
    assert "canvas_summary" in status


def test_get_grasshopper_status_number_slider_fallback(monkeypatch):
    """無 currentSettings 但 type 為 Number Slider → 從欄位兜底"""
    def fake(command_type, params=None):
        if command_type == "get_document_info":
            return {"result": {}}
        if command_type == "get_connections":
            return {"result": []}
        return {"success": True, "result": []}

    monkeypatch.setattr(bridge, "send_to_grasshopper", fake)

    def fake_all():
        return {"result": [{"id": "sl", "type": "Number Slider", "value": 8}]}

    monkeypatch.setattr(bridge, "get_all_components", fake_all)
    status = bridge.get_grasshopper_status()
    assert status["components"][0]["settings"] == {"min": 0, "max": 10, "value": 8, "rounding": 0.1}


def test_get_grasshopper_status_error(monkeypatch):
    def fake_all():
        raise RuntimeError("boom")

    monkeypatch.setattr(bridge, "send_to_grasshopper", lambda *a, **k: {"success": True, "result": {}})
    monkeypatch.setattr(bridge, "get_all_components", fake_all)
    status = bridge.get_grasshopper_status()
    assert status["status"] == "Error: boom"


def test_get_component_guide():
    guide = bridge.get_component_guide()
    assert guide["title"] == "Grasshopper Component Guide"
    assert len(guide["components"]) > 5
    assert "connectionRules" in guide
    assert "tips" in guide


def test_get_component_library():
    library = bridge.get_component_library()
    assert library["categories"]
    assert "Params" in [c["name"] for c in library["categories"]]
    assert library["dataTypes"]


# ---------- main ----------

def test_main(monkeypatch):
    ran = []
    monkeypatch.setattr(bridge.server, "run", lambda *a, **k: ran.append(1))
    bridge.main()
    assert ran == [1]


def test_main_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("crash")

    monkeypatch.setattr(bridge.server, "run", boom)
    with pytest.raises(SystemExit) as e:
        bridge.main()
    assert e.value.code == 1


# ---------- 模組層級 ----------

def test_server_exists():
    assert bridge.server is not None