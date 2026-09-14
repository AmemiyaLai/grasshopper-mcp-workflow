"""
參數設置器測試
"""

from grasshopper_tools.parameter_setter import ParameterSetter
from grasshopper_tools.component_manager import ComponentManager


def test_set_slider_properties_success(client):
    setter = ParameterSetter(client)
    client.set_response("set_slider_properties", {"success": True})
    assert setter.set_slider_properties("id-1", "120.0", 0.0, 200.0, 0.1) is True
    params = client.commands[0][1]
    assert params == {"id": "id-1", "value": "120.0", "min": 0.0, "max": 200.0, "rounding": 0.1}


def test_set_slider_properties_minimal(client):
    setter = ParameterSetter(client)
    client.set_response("set_slider_properties", {"success": True})
    assert setter.set_slider_properties("id", "5") is True
    params = client.commands[0][1]
    assert params == {"id": "id", "value": "5", "rounding": 0.1}


def test_set_slider_properties_with_id_key(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"SLIDER": "real-id"}
    setter = ParameterSetter(client, comp_mgr)
    client.set_response("set_slider_properties", {"success": True})
    assert setter.set_slider_properties("", "10", 0, 10, 0.1, "SLIDER") is True
    assert client.commands[0][1]["id"] == "real-id"


def test_set_slider_properties_id_key_not_found(client):
    setter = ParameterSetter(client)
    assert setter.set_slider_properties("", "10", component_id_key="MISSING") is False
    assert any("錯誤: 找不到組件 ID" in str(c) for c in client.print_calls)


def test_set_slider_properties_failure(client):
    setter = ParameterSetter(client)
    client.set_response("set_slider_properties", {"success": False, "error": "no"})
    assert setter.set_slider_properties("id", "1") is False
    assert any("設置 Slider 屬性失敗: no" in str(c) for c in client.print_calls)


def test_set_component_value_with_parameter(client):
    setter = ParameterSetter(client)
    client.set_response("set_component_value", {"success": True})
    assert setter.set_component_value("id", "10", "X") is True
    assert client.commands[0][1] == {"id": "id", "value": "10", "parameter": "X"}


def test_set_component_value_all_options(client):
    setter = ParameterSetter(client)
    client.set_response("set_component_value", {"success": True})
    assert setter.set_component_value("id", "10", None, 0, 100, 0.1) is True
    params = client.commands[0][1]
    assert params["min"] == 0 and params["max"] == 100 and params["rounding"] == 0.1


def test_set_component_value_id_key(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"V": "real-v"}
    setter = ParameterSetter(client, comp_mgr)
    client.set_response("set_component_value", {"success": True})
    assert setter.set_component_value("", "5", "Y", component_id_key="V") is True
    assert client.commands[0][1]["id"] == "real-v"


def test_set_component_value_id_key_not_found(client):
    setter = ParameterSetter(client)
    assert setter.set_component_value("", "5", component_id_key="MISSING") is False


def test_set_component_value_failure(client):
    setter = ParameterSetter(client)
    client.set_response("set_component_value", {"success": False, "error": "no"})
    assert setter.set_component_value("id", "5") is False
    assert any("設置組件值失敗: no" in str(c) for c in client.print_calls)


def test_set_slider_auto_range(client):
    setter = ParameterSetter(client)
    setter.component_manager.component_id_map = {"SLIDER_WIDTH": "real-w"}
    client.set_response("set_slider_properties", {"success": True})
    assert setter.set_slider("SLIDER_WIDTH", "120.0") is True
    params = client.commands[0][1]
    # determine_slider_range(SLIDER_WIDTH, 120.0) → (0.0, 240.0)
    assert params["min"] == 0.0
    assert params["max"] == 240.0


def test_set_slider_manual_range(client):
    setter = ParameterSetter(client)
    setter.component_manager.component_id_map = {"SLIDER": "real-s"}
    client.set_response("set_slider_properties", {"success": True})
    assert setter.set_slider("SLIDER", "50", 0, 100, 1.0) is True
    params = client.commands[0][1]
    assert params["min"] == 0
    assert params["max"] == 100
    assert params["rounding"] == 1.0


def test_set_slider_auto_range_partial(client):
    """只提供 min_value 時 auto_range 只補 max"""
    setter = ParameterSetter(client)
    setter.component_manager.component_id_map = {"SLIDER_RADIUS": "real-r"}
    client.set_response("set_slider_properties", {"success": True})
    assert setter.set_slider("SLIDER_RADIUS", "10", min_value=1.0) is True
    params = client.commands[0][1]
    assert params["min"] == 1.0
    assert params["max"] == 50.0  # RADIUS → max(50, 10*2)


def test_set_vector_xyz_all_success(client):
    setter = ParameterSetter(client)
    client.set_response("set_component_value", {"success": True})
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"VECTOR": "real-v"}
    setter = ParameterSetter(client, comp_mgr)
    assert setter.set_vector_xyz("VECTOR", 1.0, 2.0, 3.0) is True
    params_list = [params for _, params in client.commands]
    assert params_list[0]["parameter"] == "X" and params_list[0]["value"] == "1.0"
    assert params_list[1]["parameter"] == "Y"
    assert params_list[2]["parameter"] == "Z"


def test_set_vector_xyz_partial_failure(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"V": "real-v"}
    setter = ParameterSetter(client, comp_mgr)
    client.set_response("set_component_value", {"success": True})

    def fail_on_y(cmd_type, params):
        if params.get("parameter") == "Y":
            return {"success": False, "error": "no"}
        return {"success": True}

    client.send_command = fail_on_y
    assert setter.set_vector_xyz("V", 1, 2, 3) is False


def test_set_sliders_batch_success(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"S1": "r1", "S2": "r2"}
    setter = ParameterSetter(client, comp_mgr)
    client.set_response("set_slider_properties", {"success": True})
    configs = [("S1", "10", 0, 100, 0.1), ("S2", "20")]
    success, fail = setter.set_sliders_batch(configs)
    assert (success, fail) == (2, 0)


def test_set_sliders_batch_with_failures(client):
    comp_mgr = ComponentManager(client)
    comp_mgr.component_id_map = {"S1": "r1", "MISS": "x"}
    setter = ParameterSetter(client, comp_mgr)
    client.set_response("set_slider_properties", {"success": True})
    configs = [("S1", "10", 0, 100, 0.1), ("NOPE", "20", 0, 100, 0.1)]
    success, fail = setter.set_sliders_batch(configs)
    # NOPE 不在映射 → set_slider_properties 經由 component_id_key 查找失敗
    assert (success, fail) == (1, 1)