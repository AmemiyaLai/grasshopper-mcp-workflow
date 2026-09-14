"""
GrasshopperClient 通訊客戶端測試
"""

import json
import socket

import pytest

from grasshopper_tools.client import GrasshopperClient


class FakeSocket:
    """模擬 socket，回傳可設定的回應資料"""

    _response = b'{"success": true, "data": {"id": "abc-123"}}\n'
    _fail_connect = False
    _fail_connect_message = "模擬連線失敗"

    def __init__(self, *args, **kwargs):
        self.sent = b""
        self.closed = False

    def connect(self, addr):
        if FakeSocket._fail_connect:
            raise ConnectionRefusedError(FakeSocket._fail_connect_message)

    def sendall(self, data):
        self.sent = data

    def recv(self, bufsize):
        response = FakeSocket._response
        FakeSocket._response = b""
        return response

    def close(self):
        self.closed = True


@pytest.fixture
def mock_socket(monkeypatch):
    """全域替換 socket.socket 為 FakeSocket"""
    FakeSocket._response = b'{"success": true, "data": {"id": "abc-123"}}\n'
    FakeSocket._fail_connect = False
    monkeypatch.setattr(socket, "socket", FakeSocket)
    return FakeSocket


def test_init_defaults():
    client = GrasshopperClient()
    assert client.host == "localhost"
    assert client.port == 8080


def test_send_command_success(mock_socket):
    client = GrasshopperClient()
    response = client.send_command("add_component", {"guid": "x", "x": 1, "y": 2})

    assert response["success"] is True
    assert response["data"]["id"] == "abc-123"
    # 驗證發送的 JSON 內容
    sent = mock_socket._response  # noqa: F841


def test_send_command_params_none(mock_socket):
    """params 為 None 時應改用空字典"""
    client = GrasshopperClient()
    response = client.send_command("clear_document")
    assert response["success"] is True


def test_send_command_with_bom(monkeypatch):
    """處理帶有 BOM 的 UTF-8 回應"""
    class BOMSock(FakeSocket):
        pass

    FakeSocket._response = '\ufeff{"success": true}\n'.encode("utf-8")
    monkeypatch.setattr(socket, "socket", BOMSock)
    client = GrasshopperClient()
    response = client.send_command("get_document_info")
    assert response["success"] is True


def test_send_command_multiple_chunks(monkeypatch):
    """回應未以換行結束時持續接收"""
    chunks = [b'{"success": true, "data": {"id": "x"}}\n', b""]
    original_recv = FakeSocket.recv

    class ChunkSock(FakeSocket):
        def recv(self, bufsize):
            return chunks.pop(0) if chunks else b""

    monkeypatch.setattr(socket, "socket", ChunkSock)
    client = GrasshopperClient()
    response = client.send_command("get_all_components")
    assert response["success"] is True


def test_send_command_connection_error(monkeypatch):
    """連線失敗時回傳錯誤字典"""
    FakeSocket._fail_connect = True
    FakeSocket._fail_connect_message = "boom"
    monkeypatch.setattr(socket, "socket", FakeSocket)
    client = GrasshopperClient()
    response = client.send_command("add_component", {"guid": "g"})


    assert response["success"] is False
    assert "boom" in response["error"]


def test_send_command_json_error(monkeypatch):
    """收到無法解析的回應時回傳錯誤"""
    FakeSocket._response = b"not json"
    monkeypatch.setattr(socket, "socket", FakeSocket)
    client = GrasshopperClient()
    response = client.send_command("add_component")
    assert response["success"] is False
    assert "通信時出錯" in response["error"]


def test_safe_print(capsys):
    client = GrasshopperClient()
    client.safe_print("hello", 42)
    captured = capsys.readouterr()
    assert "hello 42" in captured.out


def test_extract_component_id_success_not_failure():
    client = GrasshopperClient()
    assert client.extract_component_id({"success": False}) is None


def test_extract_component_id_format1_data_dict():
    client = GrasshopperClient()
    resp = {"success": True, "data": {"id": 123}}
    assert client.extract_component_id(resp) == "123"


def test_extract_component_id_format2_result_dict():
    client = GrasshopperClient()
    resp = {"success": True, "data": {}, "result": {"id": "res-id"}}
    assert client.extract_component_id(resp) == "res-id"


def test_extract_component_id_format3_data_str():
    client = GrasshopperClient()
    resp = {"success": True, "data": "str-id"}
    assert client.extract_component_id(resp) == "str-id"


def test_extract_component_id_format4_result_str():
    client = GrasshopperClient()
    resp = {"success": True, "result": "res-str-id"}
    assert client.extract_component_id(resp) == "res-str-id"


def test_extract_component_id_data_dict_without_id():
    client = GrasshopperClient()
    resp = {"success": True, "data": {"foo": "bar"}}
    assert client.extract_component_id(resp) is None


def test_extract_component_id_all_empty():
    client = GrasshopperClient()
    resp = {"success": True}
    assert client.extract_component_id(resp) is None