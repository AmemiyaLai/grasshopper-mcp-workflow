"""
共享測試 Fixture

提供 FakeClient 模擬 Grasshopper 客戶端，避免測試時需要真實 socket 連線。
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from grasshopper_tools.client import GrasshopperClient


class FakeClient:
    """模擬 GrasshopperClient，記錄發送的命令並回傳可設定的回應"""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.commands: List[Tuple[str, Optional[Dict[str, Any]]]] = []
        self.responses: Dict[str, Dict[str, Any]] = {}
        self.default_response: Dict[str, Any] = {"success": True, "data": {"id": "gh-comp-id"}}
        self.print_calls: List[tuple] = []

    def send_command(self, command_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is None:
            params = {}
        self.commands.append((command_type, params))
        if command_type in self.responses:
            return self.responses[command_type]
        return dict(self.default_response)

    def set_response(self, command_type: str, response: Dict[str, Any]):
        """設定特定命令的回應"""
        self.responses[command_type] = response

    def extract_component_id(self, response: Dict[str, Any]) -> Optional[str]:
        """與 GrasshopperClient.extract_component_id 相同的邏輯"""
        if not response.get("success"):
            return None
        data = response.get("data")
        if data and isinstance(data, dict):
            comp_id = data.get("id")
            if comp_id:
                return str(comp_id)
        result = response.get("result")
        if result and isinstance(result, dict):
            comp_id = result.get("id")
            if comp_id:
                return str(comp_id)
        if data and isinstance(data, str):
            return data
        if result and isinstance(result, str):
            return result
        return None

    def safe_print(self, *args, **kwargs):
        """記錄打印呼叫，不實際輸出"""
        self.print_calls.append(args)


@pytest.fixture
def client() -> FakeClient:
    """建立 FakeClient fixture"""
    return FakeClient()


@pytest.fixture
def real_client() -> GrasshopperClient:
    """建立真實 GrasshopperClient 實例（不進行連線）"""
    return GrasshopperClient(host="localhost", port=1)


@pytest.fixture
def sample_mmd(tmp_path):
    """建立包含組件與連接的範例 MMD 文件"""
    content = """```mermaid
flowchart TD
    subgraph TOP["桌面模組"]
        SLIDER_WIDTH["Number Slider<br/>输出: 120.0<br/>GUID: e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da<br/>位置: X=100, Y=50"]
        DIVISION_X["Division<br/>GUID: 7ed9789a-7403-4eeb-9716-d6e5681f4136<br/>位置: X=300, Y=50"]
    end
    subgraph LEG_BASE["桌腳基礎模組"]
        CIRCLE_LEG_BASE["Circle<br/>GUID: 40dda121-a31b-421b-94b0-e46f5774f98e<br/>位置: X=100, Y=200"]
    end
    SLIDER_WIDTH -->|"Number"| DIVISION_X
    SLIDER_WIDTH -->|"Number"| CIRCLE_LEG_BASE
end
```
"""
    path = tmp_path / "component_info.mmd"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_placement_info(tmp_path):
    """建立範例 placement_info.json 文件"""
    data = {
        "description": "測試工作流程",
        "commands": [
            {
                "comment": "SLIDER_WIDTH",
                "type": "add_component",
                "parameters": {"guid": "e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da", "x": 100, "y": 50},
                "componentId": "SLIDER_WIDTH",
            },
            {
                "comment": "DIVISION_X",
                "type": "add_component",
                "parameters": {"guid": "7ed9789a-7403-4eeb-9716-d6e5681f4136", "x": 300, "y": 50},
                "componentId": "DIVISION_X",
            },
            {
                "comment": "SLIDER_WIDTH -> DIVISION_X",
                "type": "connect_components",
                "parameters": {
                    "sourceId": "SLIDER_WIDTH",
                    "sourceParam": "Number",
                    "targetId": "DIVISION_X",
                    "targetParam": "A",
                },
            },
        ],
    }
    path = tmp_path / "placement_info.json"
    path.write_text(data and __import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")
    return path