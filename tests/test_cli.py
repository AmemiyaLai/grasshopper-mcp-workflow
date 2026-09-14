"""
CLI 命令測試

所有 cmd_* 函式透過 monkeypatch 取代管理器類別，避免真實 socket 連線。
"""

import argparse
import json
from types import SimpleNamespace

import pytest

import grasshopper_tools.cli as cli


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


class StubManager:
    """可設定方法回傳值的通用 stub"""

    def __init__(self, **methods):
        self._methods = methods
        self.calls = []

    def __getattr__(self, name):
        if name in self._methods:
            def _call(*a, **k):
                self.calls.append((name, a, k))
                return self._methods[name]
            return _call
        raise AttributeError(name)


class StubMMD:
    """可設定解析結果的 MMDParser stub"""

    def __init__(self, sliders=None, subgraphs=None, names=None, components=None, connections=None):
        self._sliders = sliders or {}
        self._subgraphs = subgraphs or {}
        self._names = names or {}
        self._components = components or []
        self._connections = connections or []

    def parse_slider_values(self, path):
        return self._sliders

    def parse_subgraphs_from_mmd(self, path):
        return self._subgraphs

    def get_subgraph_names(self, path):
        return self._names

    def parse_component_info_mmd(self, path):
        return self._components, self._connections


# ---------- execute-placement ----------

def test_cmd_execute_placement_success(monkeypatch):
    stub = StubManager(execute_placement_info={"success": True})
    monkeypatch.setattr(cli, "PlacementExecutor", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_placement(ns(json_path="p.json", max_workers=5, save_id_map=True))
    assert e.value.code == 0
    assert stub.calls[0][2] == {"json_path": "p.json", "max_workers": 5, "save_id_map": True}


def test_cmd_execute_placement_failure(monkeypatch):
    stub = StubManager(execute_placement_info={"success": False})
    monkeypatch.setattr(cli, "PlacementExecutor", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_placement(ns(json_path="p.json", max_workers=1, save_id_map=False))
    assert e.value.code == 1


# ---------- parse-mmd ----------

def test_cmd_parse_mmd_components(sample_mmd, tmp_path):
    out = tmp_path / "out.json"
    cli.cmd_parse_mmd(ns(action="components", mmd_path=str(sample_mmd), output=str(out)))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["components"]) == 3
    assert len(data["connections"]) == 2


def test_cmd_parse_mmd_components_no_output(sample_mmd, capsys):
    cli.cmd_parse_mmd(ns(action="components", mmd_path=str(sample_mmd), output=None))
    out = capsys.readouterr().out
    assert "找到 3 個組件" in out


def test_cmd_parse_mmd_subgraphs(sample_mmd, tmp_path):
    out = tmp_path / "sg.json"
    cli.cmd_parse_mmd(ns(action="subgraphs", mmd_path=str(sample_mmd), output=str(out)))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data["subgraphs"].keys()) == {"TOP", "LEG_BASE"}
    assert data["subgraph_names"]["TOP"] == "桌面模組"


def test_cmd_parse_mmd_sliders(sample_mmd, tmp_path):
    out = tmp_path / "sl.json"
    cli.cmd_parse_mmd(ns(action="sliders", mmd_path=str(sample_mmd), output=str(out)))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["SLIDER_WIDTH"]["value"] == "120.0"


def test_cmd_parse_mmd_sliders_no_output(sample_mmd, capsys):
    cli.cmd_parse_mmd(ns(action="sliders", mmd_path=str(sample_mmd), output=None))
    assert "SLIDER_WIDTH: 120.0" in capsys.readouterr().out


# ---------- generate-json ----------

def test_cmd_generate_json(sample_mmd, tmp_path):
    out = tmp_path / "gen.json"
    cli.cmd_generate_json(ns(mmd_path=str(sample_mmd), output=str(out), description="測試描述"))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["description"] == "測試描述"
    assert len([c for c in data["commands"] if c.get("type") == "add_component"]) == 3


# ---------- update-guids ----------

def test_cmd_update_guids_default_map(tmp_path, monkeypatch, capsys):
    calls = {}
    monkeypatch.setattr(cli, "update_guids_in_json", lambda p, m: (calls.update({"p": p, "m": m}) or 3))
    cli.cmd_update_guids(ns(json_path="x.json", guid_map=None))
    assert calls["p"] == "x.json"
    assert calls["m"] is cli.DEFAULT_GUID_MAP
    assert "總共更新了 3" in capsys.readouterr().out


def test_cmd_update_guids_custom_map(tmp_path, monkeypatch, capsys):
    map_file = tmp_path / "custom.json"
    map_file.write_text(json.dumps({"old": "new"}), encoding="utf-8")
    calls = {}
    monkeypatch.setattr(cli, "update_guids_in_json", lambda p, m: (calls.update({"m": m}) or 1))
    cli.cmd_update_guids(ns(json_path="x.json", guid_map=str(map_file)))
    assert calls["m"] == {"old": "new"}


# ---------- add/delete/visibility/zoom/query ----------

def test_cmd_add_component_success(monkeypatch, capsys):
    stub = StubManager(add_component="real-id", save_id_map=None)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    cli.cmd_add_component(ns(guid="g", x=1.0, y=2.0, component_id="SLIDER"))
    assert "組件創建成功，ID: real-id" in capsys.readouterr().out
    assert stub.calls[0][2]["component_id"] == "SLIDER"
    assert any(name == "save_id_map" for name, _, _ in stub.calls)


def test_cmd_add_component_success_no_id(monkeypatch, capsys):
    stub = StubManager(add_component="rid")
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    cli.cmd_add_component(ns(guid="g", x=1.0, y=2.0, component_id=None))
    # component_id 為 None → 不呼叫 save_id_map
    assert all(name != "save_id_map" for name, _, _ in stub.calls)


def test_cmd_add_component_failure(monkeypatch):
    stub = StubManager(add_component=None)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_add_component(ns(guid="g", x=1.0, y=2.0, component_id=None))
    assert e.value.code == 1


def test_cmd_delete_component_success(monkeypatch):
    stub = StubManager(delete_component=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    assert cli.cmd_delete_component(ns(component_id="abc")) is None


def test_cmd_delete_component_failure(monkeypatch):
    stub = StubManager(delete_component=False)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_delete_component(ns(component_id="abc"))
    assert e.value.code == 1


def test_cmd_set_visibility_hidden(monkeypatch):
    stub = StubManager(set_component_visibility=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    cli.cmd_set_visibility(ns(component_id="c", hidden=True, visible=False))
    assert stub.calls[0][1] == ("c", True)


def test_cmd_set_visibility_visible(monkeypatch):
    """--visible → hidden=False，即使 --hidden 也給定（權重 else）"""
    stub = StubManager(set_component_visibility=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    cli.cmd_set_visibility(ns(component_id="c", hidden=True, visible=True))
    assert stub.calls[0][1] == ("c", False)


def test_cmd_set_visibility_failure(monkeypatch):
    stub = StubManager(set_component_visibility=False)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_set_visibility(ns(component_id="c", hidden=False, visible=False))
    assert e.value.code == 1


def test_cmd_zoom_to_components_string(monkeypatch):
    stub = StubManager(zoom_to_components=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    cli.cmd_zoom_to_components(ns(component_ids="a, b, c"))
    assert stub.calls[0][1][0] == ["a", "b", "c"]


def test_cmd_zoom_to_components_list(monkeypatch):
    stub = StubManager(zoom_to_components=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    cli.cmd_zoom_to_components(ns(component_ids=["a", "b"]))
    assert stub.calls[0][1][0] == ["a", "b"]


def test_cmd_zoom_to_components_empty(monkeypatch):
    stub = StubManager(zoom_to_components=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_zoom_to_components(ns(component_ids=" , "))
    assert e.value.code == 1


def test_cmd_query_guid_success(monkeypatch, capsys):
    stub = StubManager(get_component_guid={"name": "N", "guid": "g", "category": "c", "isBuiltIn": True})
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    cli.cmd_query_guid(ns(component_name="Number Slider"))
    assert "組件名稱: N" in capsys.readouterr().out


def test_cmd_query_guid_failure(monkeypatch):
    stub = StubManager(get_component_guid=None)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_query_guid(ns(component_name="X"))
    assert e.value.code == 1


# ---------- connect / slider / vector ----------

def test_cmd_connect_components_success(monkeypatch):
    stub = StubManager(connect_components=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "ConnectionManager", lambda component_manager=None: stub)
    assert cli.cmd_connect_components(ns(source_id="S", target_id="T", source_param="Number", target_param="A")) is None
    args = stub.calls[0][1]
    kw = stub.calls[0][2]
    assert args == ()  # source_id/target_id 以關鍵字參數傳入
    assert kw["source_id"] == "" and kw["target_id"] == ""
    assert kw["source_id_key"] == "S" and kw["target_id_key"] == "T"


def test_cmd_connect_components_failure(monkeypatch):
    stub = StubManager(connect_components=False)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "ConnectionManager", lambda component_manager=None: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_connect_components(ns(source_id="S", target_id="T", source_param=None, target_param=None))
    assert e.value.code == 1


def test_cmd_set_slider_success(monkeypatch):
    stub = StubManager(set_slider=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "ParameterSetter", lambda component_manager=None: stub)
    assert cli.cmd_set_slider(ns(component_id="S", value="10", min_value=0, max_value=100, rounding=0.1)) is None
    kw = stub.calls[0][2]
    assert kw["component_id_key"] == "S" and kw["value"] == "10"


def test_cmd_set_slider_failure(monkeypatch):
    stub = StubManager(set_slider=False)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "ParameterSetter", lambda component_manager=None: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_set_slider(ns(component_id="S", value="10", min_value=None, max_value=None, rounding=0.1))
    assert e.value.code == 1


def test_cmd_set_vector_success(monkeypatch):
    stub = StubManager(set_vector_xyz=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "ParameterSetter", lambda component_manager=None: stub)
    assert cli.cmd_set_vector(ns(component_id="V", x=1, y=2, z=3)) is None
    kw = stub.calls[0][2]
    assert kw["x"] == 1 and kw["y"] == 2 and kw["z"] == 3


def test_cmd_set_vector_failure(monkeypatch):
    stub = StubManager(set_vector_xyz=False)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "ParameterSetter", lambda component_manager=None: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_set_vector(ns(component_id="V", x=1, y=2, z=3))
    assert e.value.code == 1


# ---------- group ----------

def test_cmd_group_components_with_color(monkeypatch):
    stub = StubManager(group_components=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "GroupManager", lambda component_manager=None: stub)
    assert cli.cmd_group_components(ns(component_ids="A,B", group_name="G", color="10,20,30", color_hex=None)) is None
    kw = stub.calls[0][2]
    assert kw["component_id_keys"] == ["A", "B"]
    assert kw["color"] == (10, 20, 30)


def test_cmd_group_components_color_hex(monkeypatch):
    stub = StubManager(group_components=True)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "GroupManager", lambda component_manager=None: stub)
    cli.cmd_group_components(ns(component_ids="A", group_name="G", color=None, color_hex="#FF0000"))
    assert stub.calls[0][2]["color_hex"] == "#FF0000"


def test_cmd_group_components_failure(monkeypatch):
    stub = StubManager(group_components=False)
    monkeypatch.setattr(cli, "ComponentManager", lambda: StubManager())
    monkeypatch.setattr(cli, "GroupManager", lambda component_manager=None: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_group_components(ns(component_ids="A", group_name="G", color=None, color_hex=None))
    assert e.value.code == 1


# ---------- get-errors ----------

def test_cmd_get_errors_no_output(monkeypatch):
    stub = StubManager(get_document_errors=[{"messageType": "Error"}, {"messageType": "Warning"}])
    monkeypatch.setattr(cli, "ConnectionManager", lambda: stub)
    cli.cmd_get_errors(ns(output=None))


def test_cmd_get_errors_with_output(monkeypatch, tmp_path):
    stub = StubManager(get_document_errors=[{"messageType": "Error"}])
    monkeypatch.setattr(cli, "ConnectionManager", lambda: stub)
    out = tmp_path / "err.json"
    cli.cmd_get_errors(ns(output=str(out)))
    assert json.loads(out.read_text(encoding="utf-8"))["errors"] == [{"messageType": "Error"}]


# ---------- main ----------

def test_main_with_command(monkeypatch):
    captured = []
    ns_arg = ns(command="x", value=1)
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: ns_arg)
    monkeypatch.setattr("grasshopper_tools.cli._runner", None, raising=False)  # 無操作，確保 context 乾淨
    # 透過替代 func 驗證 dispatch
    ns_arg.func = lambda a: captured.append(a)
    cli.main()
    assert captured == [ns_arg]


def test_main_no_command(monkeypatch):
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: ns(command=None))
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 1


# ---------- zoom 失敗分支 ----------

def test_cmd_zoom_to_components_failure(monkeypatch):
    stub = StubManager(zoom_to_components=False)
    monkeypatch.setattr(cli, "ComponentManager", lambda: stub)
    with pytest.raises(SystemExit) as e:
        cli.cmd_zoom_to_components(ns(component_ids="A,B"))
    assert e.value.code == 1


# ---------- auto-set-sliders ----------

def test_cmd_auto_set_sliders_missing_mmd(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_set_sliders(ns(mmd_path=str(tmp_path / "nope.mmd"), id_map=str(tmp_path / "id.json")))
    assert e.value.code == 1


def test_cmd_auto_set_sliders_missing_id_map(tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_set_sliders(ns(mmd_path=str(mmd), id_map=str(tmp_path / "nope.json")))
    assert e.value.code == 1


def test_cmd_auto_set_sliders_no_sliders(monkeypatch, tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"S": "g"}), encoding="utf-8")
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(sliders={}))
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_set_sliders(ns(mmd_path=str(mmd), id_map=str(id_map)))
    assert e.value.code == 0


def test_cmd_auto_set_sliders_success(monkeypatch, tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"SLIDER_WIDTH": "guid1"}), encoding="utf-8")
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(sliders={"SLIDER_WIDTH": {"value": "120.0"}}))
    monkeypatch.setattr(cli, "GrasshopperClient", lambda: StubManager())
    monkeypatch.setattr(cli, "ComponentManager", lambda client=None: StubManager(load_id_map=None))
    monkeypatch.setattr(cli, "ParameterSetter", lambda client=None, component_manager=None: StubManager(set_sliders_batch=(1, 0)))
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_set_sliders(ns(mmd_path=str(mmd), id_map=str(id_map)))
    assert e.value.code == 0


def test_cmd_auto_set_sliders_partial_failure(monkeypatch, tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"SLIDER_WIDTH": "guid1"}), encoding="utf-8")
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(sliders={"SLIDER_WIDTH": {"value": "120.0"}}))
    monkeypatch.setattr(cli, "GrasshopperClient", lambda: StubManager())
    monkeypatch.setattr(cli, "ComponentManager", lambda client=None: StubManager(load_id_map=None))
    monkeypatch.setattr(cli, "ParameterSetter", lambda client=None, component_manager=None: StubManager(set_sliders_batch=(1, 1)))
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_set_sliders(ns(mmd_path=str(mmd), id_map=str(id_map)))
    assert e.value.code == 1


# ---------- auto-group-components ----------

def test_cmd_auto_group_components_missing_mmd(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_group_components(ns(mmd_path=str(tmp_path / "nope.mmd"), id_map=str(tmp_path / "id.json")))
    assert e.value.code == 1


def test_cmd_auto_group_components_missing_id_map(tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_group_components(ns(mmd_path=str(mmd), id_map=str(tmp_path / "nope.json")))
    assert e.value.code == 1


def test_cmd_auto_group_components_no_subgraphs(monkeypatch, tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"S": "g"}), encoding="utf-8")
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(subgraphs={}, names={}))
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_group_components(ns(mmd_path=str(mmd), id_map=str(id_map)))
    assert e.value.code == 0


def test_cmd_auto_group_components_success(monkeypatch, tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"SLIDER_WIDTH": "g1", "SLIDER_LENGTH": "g2"}), encoding="utf-8")
    subgraphs = {"TOP": ["SLIDER_WIDTH"], "LEG_BASE": ["SLIDER_LENGTH"]}
    names = {"TOP": "桌面", "LEG_BASE": "桌腳"}
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(subgraphs=subgraphs, names=names))
    monkeypatch.setattr(cli, "GrasshopperClient", lambda: StubManager())
    monkeypatch.setattr(cli, "ComponentManager", lambda client=None: StubManager(load_id_map=None))
    monkeypatch.setattr(cli, "GroupManager", lambda client=None, component_manager=None: StubManager(group_components_batch=(2, 0)))
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_group_components(ns(mmd_path=str(mmd), id_map=str(id_map)))
    assert e.value.code == 0


def test_cmd_auto_group_components_partial_failure(monkeypatch, tmp_path):
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"SLIDER_WIDTH": "g1"}), encoding="utf-8")
    subgraphs = {"TOP": ["SLIDER_WIDTH"], "LEG_BASE": ["MISSING"]}  # LEG_BASE 組件不在 id_map
    names = {"TOP": "桌面", "LEG_BASE": "桌腳"}
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(subgraphs=subgraphs, names=names))
    monkeypatch.setattr(cli, "GrasshopperClient", lambda: StubManager())
    monkeypatch.setattr(cli, "ComponentManager", lambda client=None: StubManager(load_id_map=None))
    monkeypatch.setattr(cli, "GroupManager", lambda client=None, component_manager=None: StubManager(group_components_batch=(1, 1)))
    with pytest.raises(SystemExit) as e:
        cli.cmd_auto_group_components(ns(mmd_path=str(mmd), id_map=str(id_map)))
    assert e.value.code == 1


# ---------- execute-full-workflow ----------

def test_cmd_execute_full_workflow_missing_placement(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_full_workflow(ns(placement_json=str(tmp_path / "nope.json"), mmd_path=str(tmp_path / "m.mmd"), id_map=str(tmp_path / "id.json"), max_workers=2, clear_first=False))
    assert e.value.code == 1


def test_cmd_execute_full_workflow_missing_mmd(tmp_path):
    placement = tmp_path / "placement.json"
    placement.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_full_workflow(ns(placement_json=str(placement), mmd_path=str(tmp_path / "nope.mmd"), id_map=str(tmp_path / "id.json"), max_workers=2, clear_first=False))
    assert e.value.code == 1


def test_cmd_execute_full_workflow_success(monkeypatch, tmp_path):
    placement = tmp_path / "placement.json"
    placement.write_text("{}", encoding="utf-8")
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"SLIDER_WIDTH": "g1", "SLIDER_LENGTH": "g2"}), encoding="utf-8")
    sliders = {"SLIDER_WIDTH": {"value": "120.0"}, "SLIDER_LENGTH": {"value": "100.0"}}
    subgraphs = {"TOP": ["SLIDER_WIDTH"], "LEG_BASE": ["SLIDER_LENGTH"]}
    names = {"TOP": "桌面", "LEG_BASE": "桌腳"}
    monkeypatch.setattr(cli, "PlacementExecutor", lambda: StubManager(execute_placement_info={"success": True}))
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(sliders=sliders, subgraphs=subgraphs, names=names))
    monkeypatch.setattr("grasshopper_tools.client.GrasshopperClient", lambda: StubManager(send_command={"success": True}))
    monkeypatch.setattr(cli, "ComponentManager", lambda client=None: StubManager(load_id_map=None))
    monkeypatch.setattr(cli, "ParameterSetter", lambda client=None, component_manager=None: StubManager(set_sliders_batch=(2, 0)))
    monkeypatch.setattr(cli, "GroupManager", lambda client=None, component_manager=None: StubManager(group_components_batch=(2, 0)))
    monkeypatch.setattr(cli, "ConnectionManager", lambda: StubManager(get_document_errors=[]))
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_full_workflow(ns(placement_json=str(placement), mmd_path=str(mmd), id_map=str(id_map), max_workers=2, clear_first=True))
    assert e.value.code == 0


def test_cmd_execute_full_workflow_clear_failed_continue(monkeypatch, tmp_path):
    placement = tmp_path / "placement.json"
    placement.write_text("{}", encoding="utf-8")
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"SLIDER_WIDTH": "g1"}), encoding="utf-8")
    sliders = {"SLIDER_WIDTH": {"value": "120.0"}}
    subgraphs = {"TOP": ["SLIDER_WIDTH"]}
    names = {"TOP": "桌面"}
    monkeypatch.setattr(cli, "PlacementExecutor", lambda: StubManager(execute_placement_info={"success": True}))
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(sliders=sliders, subgraphs=subgraphs, names=names))
    monkeypatch.setattr("grasshopper_tools.client.GrasshopperClient", lambda: StubManager(send_command={"success": False}))
    monkeypatch.setattr(cli, "ComponentManager", lambda client=None: StubManager(load_id_map=None))
    monkeypatch.setattr(cli, "ParameterSetter", lambda client=None, component_manager=None: StubManager(set_sliders_batch=(1, 0)))
    monkeypatch.setattr(cli, "GroupManager", lambda client=None, component_manager=None: StubManager(group_components_batch=(1, 0)))
    monkeypatch.setattr(cli, "ConnectionManager", lambda: StubManager(get_document_errors=[]))
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_full_workflow(ns(placement_json=str(placement), mmd_path=str(mmd), id_map=str(id_map), max_workers=2, clear_first=True))
    assert e.value.code == 0


def test_cmd_execute_full_workflow_step1_failed(monkeypatch, tmp_path):
    placement = tmp_path / "placement.json"
    placement.write_text("{}", encoding="utf-8")
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(cli, "PlacementExecutor", lambda: StubManager(execute_placement_info={"success": False}))
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_full_workflow(ns(placement_json=str(placement), mmd_path=str(mmd), id_map=str(tmp_path / "id.json"), max_workers=2, clear_first=False))
    assert e.value.code == 1


def test_cmd_execute_full_workflow_with_problems(monkeypatch, tmp_path):
    placement = tmp_path / "placement.json"
    placement.write_text("{}", encoding="utf-8")
    mmd = tmp_path / "in.mmd"
    mmd.write_text("dummy", encoding="utf-8")
    id_map = tmp_path / "id.json"
    id_map.write_text(json.dumps({"SLIDER_WIDTH": "g1"}), encoding="utf-8")
    sliders = {"SLIDER_WIDTH": {"value": "120.0"}}
    subgraphs = {"TOP": ["SLIDER_WIDTH"]}
    names = {"TOP": "桌面"}
    monkeypatch.setattr(cli, "PlacementExecutor", lambda: StubManager(execute_placement_info={"success": True}))
    monkeypatch.setattr(cli, "MMDParser", lambda: StubMMD(sliders=sliders, subgraphs=subgraphs, names=names))
    monkeypatch.setattr("grasshopper_tools.client.GrasshopperClient", lambda: StubManager(send_command={"success": True}))
    monkeypatch.setattr(cli, "ComponentManager", lambda client=None: StubManager(load_id_map=None))
    monkeypatch.setattr(cli, "ParameterSetter", lambda client=None, component_manager=None: StubManager(set_sliders_batch=(0, 1)))
    monkeypatch.setattr(cli, "GroupManager", lambda client=None, component_manager=None: StubManager(group_components_batch=(0, 1)))
    monkeypatch.setattr(cli, "ConnectionManager", lambda: StubManager(get_document_errors=[{"messageType": "Error", "componentName": "X", "message": "boom"}]))
    with pytest.raises(SystemExit) as e:
        cli.cmd_execute_full_workflow(ns(placement_json=str(placement), mmd_path=str(mmd), id_map=str(id_map), max_workers=2, clear_first=True))
    assert e.value.code == 1