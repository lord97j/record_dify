# encoding:utf-8
import json
import os
import html
from urllib.parse import urlparse

import requests

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *

@plugins.register(
    name="RecordDify",
    desire_priority=0,
    hidden=True,
    enabled=True,
    desc="使用dify自动记录聊天记录进行知识积累",
    version="0.1",
    author="lord97j",
)
class RecordDify(Plugin):

    def __init__(self):
        super().__init__()
        try:
            self.config = super().load_config()
            if self.config is None:
                logger.info("[RecordDify] config is None")
                return
            logger.info(f"[RecordDify] inited, config={self.config}")
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        except Exception as e:
            logger.error(f"[RecordDify]初始化异常：{e}")
            raise "[RecordDify] init failed, ignore "

    def on_handle_context(self, e_context: EventContext, retry_count: int = 0):
        try:
            context = e_context["context"]
            flag= False
            # 判断是群聊还是单聊
            if context.get("isgroup", False):
                # 群聊情况
                group_name = context["group_name"]
                # 遍历配置，找到匹配的群名关键词
                for conf in self.config:
                    if "group_name_keywords" in conf:
                        if any(keyword in group_name for keyword in conf["group_name_keywords"]):
                            flag = True
                            break
            else:
                # 单聊情况
                logger.debug("[RecordDify] single_chat is not supported")
                return
            
            if not flag:
                logger.debug("[RecordDify] on_handle_context. not in group")
                return

            content = context.content
            if context.type != ContextType.SHARING and context.type != ContextType.TEXT:
                return
            user = context["msg"].other_user_nickname if context.get("msg") else "default"

            inputs = {
                "text": content,
                "user": user,
                "group_name": group_name
            }
            result = self._dify_workflow_run(self.config["api_base"], self.config["api_key"], inputs, group_name)
            if result is not None and result != "None":
                reply = Reply(ReplyType.TEXT, result)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

        except Exception as e:
            if retry_count < 3:
                logger.warning(f"[RecordDify] {str(e)}, retry {retry_count + 1}")
                self.on_handle_context(e_context, retry_count + 1)
                return

            logger.exception(f"[RecordDify] {str(e)}")
            
        
    
    def _dify_workflow_run(self, api_base: str, api_key: str, inputs: object, user: str):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            }
            payload = {
                "inputs": inputs,
                "response_mode": "blocking",
                "user": user
            }
            response = requests.post(f'{api_base}/workflows/run', headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            if "data" in result and "status" in result["data"] and result["data"]["status"] == "succeeded" and "outputs" in result["data"]:
                return result["data"]["outputs"]["text"] if "text" in result["data"]["outputs"] else None
        except Exception as e:
            logger.exception(f"[RecordDify] dify {str(e)}")
        return None
    
    def _dify_upload_file(self, api_base: str, api_key: str, inputs: object, group_name: str):
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            }
            files = {
                'file': ('localfile', open(inputs['file_path'], 'rb'), 'image/png')
            }
            data = {
                'user': group_name
            }
            response = requests.post(f'{api_base}/v1/files/upload', headers=headers, files=files, data=data, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.exception(f"[RecordDify] dify upload file {str(e)}")
            return None
            