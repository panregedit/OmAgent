from pathlib import Path
from typing import Any, Dict
import requests
import time
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

ARGSCHEMA = {
    "goal": {
        "type": "string",
        "description": "The navigation goal, which can be a object with some detailed attributes. DO NOT contain parameters like 'vyaw', 'vx', 'vy'.",
        "required": True
    }
}

@registry.register_tool()
class StartNavigation(BaseTool):
    """Tool for sending navigation goals to the robot."""

    args_schema: ArgSchema = ArgSchema(**ARGSCHEMA)
    description: str = """This is a point-to-point navigation tool used to help you get to the desired location.
    You can specify a target, and the tool will try to explore and lead you to it. 
    This tool is useful for finding a specific object in the environment and navigating to it. """ #But it not suitable for some fine-grained movements."""

    def _get_navigation_status(self) -> Dict[str, Any]:
        """获取当前导航状态

        Returns:
            Dict[str, Any]: 包含导航状态的响应
        """
        try:
            response = requests.get("http://localhost:8765/navigation_status/")
            response.raise_for_status()
            result = response.json()
            status_code = result["status"]
            status_name = NavigationStatus(status_code).name
            return {
                "success": result["code"] == 0,
                "status": status_code,
                "status_description": status_name
            }
        except Exception as e:
            return {
                "success": False,
                "status": -1,
                "status_description": "ERROR"
            }

    def _run(self, goal: str) -> Dict[str, Any]:
        """Send navigation goal to the navigation server and monitor status.

        Args:
            goal (str): Target location name.

        Returns:
            Dict[str, Any]: Response containing code, msg and result.
        """
        try:
            # 发送导航请求到导航服务器
            response = requests.post(
                "http://localhost:8765/start_navigation/",
                json={"goal": goal}
            )
            response.raise_for_status()
            result = response.json()
            
            if not result["code"] == 0:
                return {
                    "code": 500,
                    "msg": "failed",
                    "result": f"Failed to start navigation: {result['message']}"
                }
            
            # 开始轮询导航状态
            while True:
                status_result = self._get_navigation_status()
                
                if not status_result["success"]:
                    return {
                        "code": 500,
                        "msg": "failed",
                        "result": "Failed to get navigation status"
                    }
                
                status_code = status_result["status"]
                
                # 如果导航完成或不可达，则结束轮询
                if status_code in [NavigationStatus.COMPLETED, NavigationStatus.UNREACHABLE]:
                    return {
                        "code": 0 if status_code == NavigationStatus.COMPLETED else 500,
                        "msg": "success" if status_code == NavigationStatus.COMPLETED else "failed",
                        "result": "Navigation has been completed, and the target object is nearby" if status_code == NavigationStatus.COMPLETED else "Navigation failed, the target object is in the obstacle, and the path is not reachable."
                    }
                
                # 等待一段时间后再次查询
                time.sleep(1.0)
            
        except Exception as e:
            return {
                "code": 500,
                "msg": "failed",
                "result": f"Failed to start navigation: {str(e)}"
            }
