from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

image_url = "https://image20221016.oss-cn-shanghai.aliyuncs.com/images.jpg"

@register("astrbot_plugin_hello-bye", "tinker", "一个简单的入群和退群信息提示插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

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
            group_id = raw_message.get("group_id")
            user_id = raw_message.get("user_id")
            # 发送欢迎消息
            welcome_message = f"✨✨✨ 欢迎新成员: {user_id} 进群！"
            # logger.info(f"群 {group_id} 新成员 {user_id} 加入 url_image: {image_url}")
            yield event.make_result().message(welcome_message).url_image(image_url)

        elif raw_message.get("notice_type") == "group_decrease":
            # 群成员减少事件
            group_id = raw_message.get("group_id")
            user_id = raw_message.get("user_id")
            # 发送告别消息
            goodbye_message = f"成员 {user_id} 离开了我们！"
            yield event.plain_result(goodbye_message)