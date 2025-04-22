import asyncio
from datetime import datetime, timedelta

import aiohttp

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
import astrbot.api.message_components as Comp

# image_url = "https://image20221016.oss-cn-shanghai.aliyuncs.com/images.jpg"

@register("astrbot_plugin_hello-bye", "tinker", "一个简单的入群和退群信息提示插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.is_send_welcome = config.get("is_send_welcome", False)
        self.is_send_bye = config.get("is_send_bye", True)
        self.is_debug = config.get("is_debug", False)
        self.target_groups = config.get("target_groups", [])
        self.groups = config.get("groups", [])
        self.welcome_text = config.get("welcome_text", "欢迎新成员加入！")
        self.welcome_img = config.get("welcome_img", None)
        self.last_day = None
        self.napcat_host = config.get("napcat_host", "127.0.0.1:3000")
        # 定时任务
        self.scheduler_task = asyncio.create_task(self.scheduler_task())

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        if hasattr(self, "scheduler_task"):
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                logger.debug("调度器任务已成功取消")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_group_add(self, event: AstrMessageEvent):
        """处理所有类型的消息事件"""
        # logger.info(f"Received message_obj: {event.message_obj}")
        # 没有 message_obj 或 raw_message 属性时，直接返回
        if not hasattr(event, "message_obj") or not hasattr(event.message_obj, "raw_message"):
            return

        raw_message = event.message_obj.raw_message
        # 处理 raw_message
        if not raw_message or not isinstance(raw_message, dict):
            return
        # 确保是 notice 类型的消息
        if raw_message.get("post_type") != "notice":
            return

        if raw_message.get("notice_type") == "group_increase":
            # 群成员增加事件
            if not self.is_send_welcome:
                return
            group_id = raw_message.get("group_id")
            # 检查是否在白名单中
            if str(group_id) not in self.groups:
                return
            user_id = raw_message.get("user_id")
            # 发送欢迎消息

            if self.welcome_img:
                image_url = self.welcome_img
                chain = [
                    Comp.At(qq=user_id),
                    Comp.Plain(self.welcome_text),
                    Comp.Image.fromURL(image_url),
                ]
                yield event.chain_result(chain)
            else:
                chain = [
                    Comp.At(qq=user_id),
                    Comp.Plain(self.welcome_text),
                ]
                yield event.chain_result(chain)

        elif raw_message.get("notice_type") == "group_decrease":
            # 群成员减少事件
            if not self.is_send_bye:
                return
            group_id = raw_message.get("group_id")
            # 检查是否在白名单中
            if str(group_id) not in self.groups:
                return
            user_id = raw_message.get("user_id")
            # 发送告别消息
            goodbye_message = f"群友 {user_id} 离开了我们！"
            yield event.plain_result(goodbye_message)

    async def groups_sign_in(self):
        """群签到"""
        for group_id in self.target_groups:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                                        f"http://{self.napcat_host}/send_group_sign",
                                        json={"group_id": group_id},) as response:
                        if response.status == 200:
                            logger.info(f"群 {group_id} 签到成功")
                        else:
                            logger.error(f"群 {group_id} 签到失败: {response.status}")
            except Exception as e:
                logger.error(f"群 {group_id} 签到异常: {e}")

    async def scheduler_task(self):
        """定时任务"""
        # 这里可以实现定时任务的逻辑
        while True:
            now = datetime.utcnow() + timedelta(hours=8)
            current_day = now.day
            if self.is_debug:
                logger.debug("当前时间: %s", now.isoformat())
            if current_day != self.last_day or self.last_day is None:
                self.last_day = current_day
                if self.is_debug:
                    logger.debug("调度器触发，当前日期: %s", now.isoformat())
                await self.groups_sign_in()
            await asyncio.sleep(1) # 每秒检查一次