from pathlib import Path
from typing import Any, Dict, Optional, Union
import json
from urllib.parse import urljoin
import requests
from websocket import create_connection
from pydantic import Field, BaseModel
import websocket

from omagent_core.utils.logger import logging
from omagent_core.utils.registry import registry
from omagent_core.tool_system.base import ArgSchema, BaseTool
from omagent_core.models.llms.base import BaseLLM, PromptTemplate
from omagent_core.models.llms.base import BaseLLMBackend
from omagent_core.models.llms.schemas import Message

CURRENT_PATH = Path(__file__).parents[0]

VOICE_OPEN_ENDPOINT = "/signalservice/voicetalk/open"
VOICE_CLOSE_ENDPOINT = "/signalservice/voicetalk/close"

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
    request_url: str
    
    def model_post_init(self, __context: Any) -> None:
        self.address, self.session = self.open_tts_websocket()

    def _run(self, goal: str, max_chat_turns: int = 10) -> str:
        note = self.stm(self.workflow_instance_id)["note"]

        sys_prompt = PromptTemplate.from_file(CURRENT_PATH.joinpath("sys_prompt.prompt"), role="system")
        sys_prompt = sys_prompt.format(goal=goal, task=note.current_task().instruction, steps=note.current_task().summarize_steps(include_unfinished=True))

        context = [Message.system(sys_prompt)]

        for _ in range(max_chat_turns):
            result = ChatResult.model_validate_json(self.llm.generate(records=context, response_format=ChatResult)["choices"][0]["message"]["content"])
            logging.info(f"Chat result: {json.dumps(result.model_dump(), indent=4, ensure_ascii=False)}")
            # if result.is_done:
            #     # self.callback.send_block(agent_id=self.workflow_instance_id, msg=result.chat)
            #     self.audio_output(output_prompt=result.chat)
            #     return {
            #         "code": 0,
            #         "msg": "success",
            #         "result": result.result
            #     }
            # context.append(Message.assistant(result.chat))
            # user_input = self.audio_read_input(input_prompt=result.chat)
            self.audio_output(output_prompt=result.chat)
            if result.is_done:
                return {
                    "code": 0,
                    "msg": "success",
                    "result": result.result
                }
            else:
                user_input = self.audio_input()
                context.append(Message.user(user_input))

            if result.is_done:
                break

        return {
            "code": 500,
            "msg": "failed",
            "result": "Exceeded max chat turns when communicating with human."
        }
            
    def open_tts_websocket(self):
        url = urljoin(self.request_url, VOICE_OPEN_ENDPOINT)
        try:
            response = requests.get(url, timeout=10)
            result = response.json()
            logging.info(f"Open audio websocket connection: {result}")
            if result.get('code') == '0':
                result_data = result.get('data')
                address = result_data.get('address')
                session = result_data.get('session')
                if address and session:
                    logging.info(f"Get WebSocket address: {address}, session ID: {session}")
                    return address, session
                else:
                    raise Exception("Failed to get WebSocket address or session ID")
            else:
                raise Exception(f"Open audio websocket connection failed: {result.get('message', 'Unknown error')}")
        except Exception as e:
            raise Exception(f"Open audio websocket connection failed: {e}")

    def audio_input(self):
        ws = create_connection(self.address)
        logging.info(f"WebSocket connection established")
        data = {
            "type": "asr-open",
            "message": ""
        }
        ws.send(json.dumps(data))
        logging.info(f"Bot now is listening...")
        all_text = ""
        continue_loop = True
        
        while True:
            try:
                message = ws.recv()
                logging.info(f"Received message: {message}")
                
                try:
                    if isinstance(message, bytes):
                        message = message.decode('utf-8')
                    data = json.loads(message)
                    
                    if "type" in data and data["type"] == "asr-text":
                        all_text += data["message"]
                        logging.info(f"Accumulated ASR text: {all_text}")
                    elif "type" in data and data["type"] == "asr-close":
                        logging.info("ASR ended")
                        logging.info(f"Final accumulated text: {all_text}")
                        continue_loop = False 
                except json.JSONDecodeError:
                    if isinstance(message, bytes):
                        message = message.decode('utf-8')
                    all_text += message
                    print(f"None JSON message: {message}")
                    
            except websocket.WebSocketConnectionClosedException:
                print("WebSocket connection closed")
                break
            except Exception as e:
                print(f"Receive message error: {e}")
                break
            
            if continue_loop == False:
                break
            
            
        ws.close()
        logging.info(f"WebSocket connection closed")
        return all_text

        
    def audio_output(self, output_prompt: str) -> Dict:
        try:
            websocket_url = self.address
            logging.info(f"WebSocket address: {websocket_url}")
            ws = create_connection(websocket_url)
            data = {
                "type": "broadcast",
                "asr": "false",
                "message": output_prompt
            }
            ws.send(json.dumps(data))
            logging.info(f"Send tts text: {output_prompt}")
            ws.close()
            logging.info(f"WebSocket connection closed")
            logging.info(f"Send tts text success")
        except Exception as e:
            raise Exception(f"Send tts text failed: {e}")