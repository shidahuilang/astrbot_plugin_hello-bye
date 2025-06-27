import json
import aiohttp
import random
from pathlib import Path


from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
import astrbot.api.message_components as Comp


# image_url = "https://image20221016.oss-cn-shanghai.aliyuncs.com/images.jpg"
async def is_valid_image_url(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=5) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Error checking image URL: {e}")
        return False

@register("astrbot_plugin_hello-bye", "tinker", "一个简单的入群和退群信息提示插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.is_send_welcome = config.get("is_send_welcome", False)
        self.is_at = config.get("is_at", True)
        self.is_send_bye = config.get("is_send_bye", True)
        self.is_debug = config.get("is_debug", False)
        self.black_groups = config.get("black_groups", [])
        self.white_groups = config.get("white_groups", [])
        self.welcome_text = config.get("welcome_text", "欢迎新成员加入！")
        self.welcome_img = config.get("welcome_img", [])
        self.bye_text = config.get("bye_text", "群友{username}({userid})退群了!")
        self.bye_img = config.get("bye_img", [])

        # 数据目录
        data_dir = Path("data/hello-bye")
        data_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = data_dir / "data.json"

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("设置欢迎消息", alias={"设置入群信息", "设置入群提示", "设置欢迎信息"})
    async def set_hello_message(self, event: AstrMessageEvent, message: str):
        """设置欢迎消息"""
        if event.is_private_chat():
            yield event.plain_result("请在群聊中使用此命令")
            return
        group_id = event.get_group_id()
        # 在json文件中，把群号和消息存储为键值对
        if not self.json_path.exists():
            logger.info("数据文件不存在，创建新的数据文件")
            with open(self.json_path, "w") as f:
                json.dump({}, f)
        # 读取json文件
        with open(self.json_path, "r") as f:
            data = json.load(f)

        data[str(group_id)] = message
        with open(self.json_path, "w") as f:
            json.dump(data, f)
        yield event.plain_result(f"欢迎消息已设置为：{message}")

    @filter.command("查看欢迎消息", alias={"查看入群信息", "查看入群提示", "查看欢迎信息"})
    async def get_hello_message(self, event: AstrMessageEvent):
        """查看欢迎消息"""
        if event.is_private_chat():
            yield event.plain_result("请在群聊中使用此命令")
            return
        group_id = event.get_group_id()
        # 读取json文件
        if not self.json_path.exists():
            yield event.plain_result("数据文件不存在")
            return
        with open(self.json_path, "r") as f:
            data = json.load(f)

        message = data.get(str(group_id), None)
        if message:
            yield event.plain_result(f"欢迎消息为：{message}")
        else:
            yield event.plain_result("没有设置欢迎消息")

    def check_send(self, group_id: str) -> bool:
        """检查是否发送欢迎或退群消息"""
        # 检查黑名单
        if self.black_groups and str(group_id) in self.black_groups:
            return False
        # 检查白名单
        if self.white_groups and str(group_id) not in self.white_groups:
            return False
        return True

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
            # 检查是否在黑名单中
            if not self.check_send(group_id):
                return
            user_id = raw_message.get("user_id")
            # 发送欢迎消息

            welcome_message = self.welcome_text
            # 检查是否有自定义欢迎消息
            if self.json_path.exists():
                with open(self.json_path, "r") as f:
                    data = json.load(f)
                    if str(group_id) in data:
                        welcome_message = data[str(group_id)]

            if self.welcome_img:
                image_url = random.choice(self.welcome_img)
                valid_image = await is_valid_image_url(image_url)
                if valid_image:
                    chain = [
                        Comp.At(qq=user_id) if self.is_at else Comp.Plain(""),
                        Comp.Plain(welcome_message),
                        Comp.Image.fromURL(image_url),
                    ]
                else:
                    logger.warning(f"Invalid image URL: {image_url}")
                    chain = [
                        Comp.At(qq=user_id) if self.is_at else Comp.Plain(""),
                        Comp.Plain(welcome_message),
                    ]
                yield event.chain_result(chain)
            else:
                chain = [
                    Comp.At(qq=user_id) if self.is_at else Comp.Plain(""),
                    Comp.Plain(welcome_message),
                ]
                yield event.chain_result(chain)

        elif raw_message.get("notice_type") == "group_decrease":
            # 群成员减少事件
            if not self.is_send_bye:
                return
            group_id = raw_message.get("group_id")
            # 检查是否在黑名单中
            if not self.check_send(group_id):
                return
            user_id = raw_message.get("user_id")
            # 获取用户昵称
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            info = await client.get_stranger_info(user_id=user_id, no_cache=True)
            # 将用户昵称和ID替换到消息中
            username = info.get("nickname", "未知用户")
            goodbye_message = self.bye_text.format(username=username, userid=user_id)
            yield event.plain_result(goodbye_message)