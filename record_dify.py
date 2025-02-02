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
    esire_priority=10,
    hidden=False,
    enabled=False,
    desc="使用dify自动记录聊天记录进行知识积累",
    version="0.2",
    author="lord97j",
)
class RecordDify(Plugin):

    def __init__(self):
        super().__init__()
        try:
            self.config = super().load_config()
            if self.config is None:
                self.config = self._load_config_template()
            logger.info(f"[RecordDify] inited, config={self.config}")
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        except Exception as e:
            logger.error(f"[RecordDify]初始化异常：{e}")
            raise "[RecordDify] init failed, ignore "

    def on_handle_context(self, e_context: EventContext):
        try:
            context = e_context["context"]
            logger.info(f"[RecordDify] on_handle_context. context={context} config={self.config}")
            flag= False
            # 判断是群聊还是单聊
            if context.get("isgroup", False):
                # 群聊情况
                group_name = context["group_name"]
                # 遍历配置，找到匹配的群名关键词
                if "group_name_keyword_white_list" in self.config:
                    if any(keyword in group_name for keyword in self.config["group_name_keyword_white_list"]):
                        flag = True
            else:
                # 单聊情况
                logger.debug("[RecordDify] single_chat is not supported")
                return
            
            if not flag:
                logger.debug("[RecordDify] on_handle_context. not in group")
                return

            content = context.content
            if context.type != ContextType.SHARING and context.type != ContextType.TEXT:
                logger.debug("[RecordDify] on_handle_context. not text or sharing")
                return
            user = context["msg"].other_user_nickname if context.get("msg") else "default"

            inputs = {
                "text": content,
                "user": user,
                "group_name": group_name
            }
            self._dify_workflow_run(self.config["api_base"], self.config["api_key"], inputs, group_name)
            e_context.action = EventAction.CONTINUE

        except Exception as e:
            e_context.action = EventAction.CONTINUE
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
            requests.post(f'{api_base}/workflows/run', headers=headers, json=payload, timeout=60)
        except Exception as e:
            logger.exception(f"[RecordDify] dify {str(e)}")
        return None