from pathlib import Path
from typing import Any, Dict
import requests
from enum import IntEnum

from omagent_core.utils.registry import registry
from omagent_core.tool_system.base import ArgSchema, BaseTool

CURRENT_PATH = Path(__file__).parents[0]

# 定义导航状态枚举
class NavigationStatus(IntEnum):
    NOT_STARTED = 0  # 未开始导航
    NAVIGATING = 1   # 正在导航中
    COMPLETED = 2    # 导航结束
    UNREACHABLE = 3  # 导航点不可达

ARGSCHEMA = {}

@registry.register_tool()
class GetNavigationStatus(BaseTool):
    """Tool for getting the current navigation status of the robot."""

    args_schema: ArgSchema = ArgSchema(**ARGSCHEMA)
    description: str = """This tool is used to get the current navigation status of the robot.
    Status codes:
    - 0: Navigation not started
    - 1: Currently navigating
    - 2: Navigation completed
    - 3: Target location unreachable"""

    def _run(self) -> Dict[str, Any]:
        """Get the current navigation status from the navigation server.

        Returns:
            Dict[str, Any]: Response containing the navigation status.
        """
        try:
            # 发送获取状态请求到导航服务器
            response = requests.get("http://localhost:8765/navigation_status/")
            response.raise_for_status()
            result = response.json()
            
            # 获取状态码并转换为对应的状态描述
            status_code = result["status"]
            status_name = NavigationStatus(status_code).name
            
            return {
                "success": result["code"] == 0,
                "status": status_code,
                "status_description": status_name,
                "message": f"当前导航状态: {status_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "status": -1,
                "status_description": "ERROR",
                "message": f"获取导航状态失败: {str(e)}"
            } 