from pathlib import Path
from typing import Any, Dict, Optional, Union
import json

from pydantic import Field, BaseModel

from omagent_core.utils.logger import logging
from omagent_core.utils.registry import registry
from omagent_core.tool_system.base import ArgSchema, BaseTool
from omagent_core.models.llms.base import BaseLLM, PromptTemplate
from omagent_core.models.llms.base import BaseLLMBackend
from ..utils.channel_manager import ChannelFactoryManager
from omagent_core.models.llms.schemas import Message

CURRENT_PATH = Path(__file__).parents[0]

ARGSCHEMA = {
    "goal": {
        "type": "string",
        "description": "The goal you want to achieve during the conversation.",
        "required": True,
    },
}

class ChatResult(BaseModel):
    thinking: str = Field(description="Please think step by step before you drop next message. Focus on your goal and don't be distracted.")
    result: str = Field(description="Summarize the result of your conversation with human. Focus on your goal, what the human have done and what you have learned.")
    is_done: bool = Field(description="Please use the context of the conversation and your background information to determine if your goal has been reached, return True if it has been accomplished, otherwise return False")
    chat: str = Field(description="The chat content you will say to human. If you already reach your goal, please end the conversation politely.")

@registry.register_tool()
class Communicate(BaseLLMBackend, BaseTool):
    """Tool for making Unitree Go2 robot to communicate with human."""

    class Config:
        """Configuration for this pydantic object."""

        extra = "allow"
        arbitrary_types_allowed = True

    args_schema: ArgSchema = ArgSchema(**ARGSCHEMA)
    description: str = "This tool is used to communicate with human. When you need help of person like interacting with the environment or getting some informations you are lacking, you can use this tool to ask and get answer."

    def _run(self, goal: str, max_chat_turns: int = 10) -> str:
        note = self.stm(self.workflow_instance_id)["note"]

        sys_prompt = PromptTemplate.from_file(CURRENT_PATH.joinpath("sys_prompt.prompt"), role="system")
        sys_prompt = sys_prompt.format(goal=goal, task=note.current_task().instruction, steps=note.current_task().summarize_steps(include_unfinished=True))

        context = [Message.system(sys_prompt)]

        for _ in range(max_chat_turns):
            result = ChatResult.model_validate_json(self.llm.generate(records=context, response_format=ChatResult)["choices"][0]["message"]["content"])
            logging.info(f"Chat result: {json.dumps(result.model_dump(), indent=4, ensure_ascii=False)}")
            if result.is_done:
                # self.callback.send_block(agent_id=self.workflow_instance_id, msg=result.chat)
                self.audio_output(output_prompt=result.chat)
                return {
                    "code": 0,
                    "msg": "success",
                    "result": result.result
                }
            context.append(Message.assistant(result.chat))
            user_input = self.audio_read_input(input_prompt=result.chat)
            context.append(Message.user(user_input))

            if result.is_done:
                break

        return {
            "code": 500,
            "msg": "failed",
            "result": "Exceeded max chat turns when communicating with human."
        }
    
    def audio_read_input(self, input_prompt: str) -> Dict:
        import requests
        import json
        
        # Get voice input from the user
        input_url = "http://localhost:6666/voice/input"
        input_payload = {
            "prompt": input_prompt,
            "workflow_instance_id": self.workflow_instance_id
        }
        input_response = requests.post(
            input_url, 
            headers={"Content-Type": "application/json"},
            data=json.dumps(input_payload)
        )

        logging.info(f".... Audio input finished ....")
        
        # Parse the response
        response_data = input_response.json()["messages"][0]["content"][0]["data"]
        logging.info(f".... Input message: {response_data} ....")
        
        # Format the response to match the expected structure
        return response_data
    
    def audio_output(self, output_prompt: str) -> Dict:
        import requests
        import json
        
        output_url = "http://localhost:6666/voice/output"
        output_payload = {
            "msg": output_prompt,
            "agent_id": self.workflow_instance_id
        }
        output_response = requests.post(
            output_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(output_payload)
        )