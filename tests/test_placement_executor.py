"""
Placement 執行器測試
"""

from grasshopper_tools.placement_executor import PlacementExecutor
from grasshopper_tools.component_manager import ComponentManager
from grasshopper_tools.connection_manager import ConnectionManager


def test_execute_placement_info_success(client, sample_placement_info):
    client.set_response("connect_components", {"success": True})
    mgr = PlacementExecutor(client)

    result = mgr.execute_placement_info(str(sample_placement_info), max_workers=2, save_id_map=False)

    assert result["success"] is True
    assert result["add_success"] == 2
    assert result["add_fail"] == 0
    assert result["connect_success"] == 1
    assert result["connect_fail"] == 0
    assert "total_time" in result
    # 未保存 id map
    assert result["component_id_map_size"] == 2


def test_execute_placement_info_save_id_map(client, sample_placement_info, monkeypatch):
    calls = []
    monkeypatch.setattr(ComponentManager, "save_id_map", lambda self, p=None: calls.append(p))
    mgr = PlacementExecutor(client)

    result = mgr.execute_placement_info(
        str(sample_placement_info), max_workers=2, save_id_map=True, id_map_path="abc.json"
    )
    assert result["success"] is True
    assert "abc.json" in calls


def test_execute_placement_info_save_id_map_default(client, sample_placement_info, monkeypatch):
    """未指定 id_map_path 時使用預設路徑"""
    calls = []
    monkeypatch.setattr(ComponentManager, "save_id_map", lambda self, p=None: calls.append(p))
    mgr = PlacementExecutor(client)
    result = mgr.execute_placement_info(str(sample_placement_info), max_workers=2, save_id_map=True)
    assert result["success"] is True
    assert None in calls


def test_execute_placement_info_unreadable(tmp_path):
    mgr = PlacementExecutor()
    result = mgr.execute_placement_info(str(tmp_path / "missing.json"))
    assert result == {"success": False, "error": "無法讀取命令文件"}


def test_execute_placement_info_with_failures(client, sample_placement_info):
    """部分組件創建失敗時仍繼續執行連接"""
    client.set_response("add_component", {"success": False, "error": "no"})
    client.set_response("connect_components", {"success": True})
    mgr = PlacementExecutor(client)
    result = mgr.execute_placement_info(str(sample_placement_info), max_workers=2, save_id_map=False)
    assert result["add_success"] == 0
    assert result["add_fail"] == 2
    # add 全失敗 → id map 空 → 連接查無 source/target id 也失敗
    assert result["connect_success"] == 0
    assert result["connect_fail"] == 1
    assert result["success"] is False
    # 創建失敗時組件 id map 應為空
    assert result["component_id_map_size"] == 0


def test_execute_placement_info_connect_failures(client, sample_placement_info):
    client.set_response("connect_components", {"success": False, "error": "boom"})
    mgr = PlacementExecutor(client)
    result = mgr.execute_placement_info(str(sample_placement_info), max_workers=2, save_id_map=False)
    assert result["connect_success"] == 0
    assert result["connect_fail"] == 1
    assert result["success"] is False


def test_default_construction():
    """未提供 client 時應建立預設實例（不會連線）"""
    mgr = PlacementExecutor()
    assert isinstance(mgr.component_manager, ComponentManager)
    assert isinstance(mgr.connection_manager, ConnectionManager)