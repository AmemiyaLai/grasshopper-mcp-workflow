"""
連接管理器測試
"""

from grasshopper_tools.connection_manager import ConnectionManager
from grasshopper_tools.component_manager import ComponentManager


def test_connect_components_simple_success(client):
    mgr = ConnectionManager(client)
    client.set_response("connect_components", {"success": True})
    assert mgr.connect_components("src", "tgt") is True
    assert client.commands[0][1] == {"sourceId": "src", "targetId": "tgt"}


def test_connect_components_with_params(client):
    mgr = ConnectionManager(client)
    client.set_response("connect_components", {"success": True})
    assert mgr.connect_components("src", "tgt", "Number", "A") is True
    params = client.commands[0][1]
    assert params["sourceParam"] == "Number"
    assert params["targetParam"] == "A"


def test_connect_components_source_id_key(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"SLIDER": "real-src"}
    mgr = ConnectionManager(client, comp_mgr)
    client.set_response("connect_components", {"success": True})
    assert mgr.connect_components("", "tgt", source_id_key="SLIDER") is True
    assert client.commands[0][1]["sourceId"] == "real-src"


def test_connect_components_target_id_key(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"DIV": "real-tgt"}
    mgr = ConnectionManager(client, comp_mgr)
    client.set_response("connect_components", {"success": True})
    assert mgr.connect_components("src", "", target_id_key="DIV") is True
    assert client.commands[0][1]["targetId"] == "real-tgt"


def test_connect_components_source_key_not_found(client):
    mgr = ConnectionManager(client)
    assert mgr.connect_components("", "tgt", source_id_key="MISSING") is False
    assert any("找不到源組件 ID" in str(c) for c in client.print_calls)


def test_connect_components_target_key_not_found(client):
    mgr = ConnectionManager(client)
    assert mgr.connect_components("src", "", target_id_key="MISSING") is False
    assert any("找不到目標組件 ID" in str(c) for c in client.print_calls)


def test_connect_components_failure(client):
    mgr = ConnectionManager(client)
    client.set_response("connect_components", {"success": False, "error": "boo"})
    assert mgr.connect_components("src", "tgt") is False
    assert any("連接失敗: boo" in str(c) for c in client.print_calls)


def test_connect_components_parallel_all_success(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"S1": "s1", "T1": "t1", "S2": "s2", "T2": "t2"}
    mgr = ConnectionManager(client, comp_mgr)
    client.set_response("connect_components", {"success": True})

    commands = [
        {"parameters": {"sourceId": "S1", "targetId": "T1"}, "comment": "c1"},
        {"parameters": {"sourceId": "S2", "targetId": "T2"}, "comment": "c2"},
    ]
    success, fail = mgr.connect_components_parallel(commands, max_workers=2)
    assert (success, fail) == (2, 0)


def test_connect_components_parallel_missing_ids(client):
    """分別測試來源與目標 ID 找不到的情况"""
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"S1": "s1", "T2": "t2"}
    mgr = ConnectionManager(client, comp_mgr)

    commands = [
        {"parameters": {"sourceId": "SX", "targetId": "T1"}},  # source 缺少
        {"parameters": {"sourceId": "S1", "targetId": "TX"}},  # target 缺少
    ]
    success, fail = mgr.connect_components_parallel(commands, max_workers=2)
    assert (success, fail) == (0, 2)

    msgs = [str(c) for c in client.print_calls]
    assert any("找不到源組件 ID" in m for m in msgs)
    assert any("找不到目標組件 ID" in m for m in msgs)


def test_connect_components_parallel_send_failure(client):
    """send_command 回傳失敗時計入失敗"""
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"S1": "s1", "T1": "t1"}
    mgr = ConnectionManager(client, comp_mgr)
    client.set_response("connect_components", {"success": False, "error": "no"})
    commands = [{"parameters": {"sourceId": "S1", "targetId": "T1"}}]
    success, fail = mgr.connect_components_parallel(commands, max_workers=1)
    assert (success, fail) == (0, 1)


def test_connect_components_parallel_exception(client):
    """execute_connect 拋出例外時計入失敗"""
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"S1": "s1", "T1": "t1"}
    mgr = ConnectionManager(client, comp_mgr)

    def boom(*args, **kwargs):
        raise RuntimeError("crash")

    client.send_command = boom
    commands = [{"parameters": {"sourceId": "S1", "targetId": "T1"}}]
    success, fail = mgr.connect_components_parallel(commands, max_workers=1)
    assert (success, fail) == (0, 1)
    assert any("執行時發生異常" in str(c) for c in client.print_calls)


def test_get_document_errors_success(client):
    client.set_response(
        "get_document_errors",
        {"success": True, "data": {"errors": [{"messageType": "Error"}]}},
    )
    mgr = ConnectionManager(client)
    errors = mgr.get_document_errors()
    assert errors == [{"messageType": "Error"}]


def test_get_document_errors_result_key(client):
    client.set_response(
        "get_document_errors",
        {"success": True, "result": {"errors": [{"m": "x"}]}},
    )
    mgr = ConnectionManager(client)
    assert mgr.get_document_errors() == [{"m": "x"}]


def test_get_document_errors_failure(client):
    client.set_response("get_document_errors", {"success": False, "error": "no"})
    mgr = ConnectionManager(client)
    assert mgr.get_document_errors() == []
    assert any("獲取錯誤失敗" in str(c) for c in client.print_calls)


def test_fix_connection(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"S": "s-r", "T": "t-r"}
    mgr = ConnectionManager(client, comp_mgr)
    client.set_response("connect_components", {"success": True})
    assert mgr.fix_connection("", "", "P", "Q", "S", "T") is True
    params = client.commands[0][1]
    assert params == {
        "sourceId": "s-r",
        "targetId": "t-r",
        "sourceParam": "P",
        "targetParam": "Q",
    }