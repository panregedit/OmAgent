from pathlib import Path
from typing import Any, Dict
import requests

from omagent_core.utils.registry import registry
from omagent_core.tool_system.base import ArgSchema, BaseTool

CURRENT_PATH = Path(__file__).parents[0]

ARGSCHEMA = {
    "goal": {
        "type": "string",
        "description": "导航目标名称",
        "required": True
    }
}

@registry.register_tool()
class StartNavigation(BaseTool):
    """Tool for sending navigation goals to the robot."""

    args_schema: ArgSchema = ArgSchema(**ARGSCHEMA)
    description: str = """This tool is used to send navigation goals to the robot. 
    You can specify a target location name, and the robot will navigate to that location."""

    def _run(self, goal: str) -> Dict[str, Any]:
        """Send navigation goal to the navigation server.

        Args:
            goal (str): Target location name.

        Returns:
            Dict[str, Any]: Response from the navigation server.
        """
        try:
            # 发送导航请求到导航服务器
            response = requests.post(
                "http://localhost:8765/start_navigation/",
                json={"goal": goal}
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": result["code"] == 0,
                "message": result["message"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"导航请求失败: {str(e)}"
            }
