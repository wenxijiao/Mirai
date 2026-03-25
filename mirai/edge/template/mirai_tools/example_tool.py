from datetime import datetime
from mirai.utils.tool import mirai_tool 

@mirai_tool(description="获取边缘设备当前的本地时间")
def get_device_time() -> str:
    now = datetime.now()
    return f"边缘设备当前时间是: {now.strftime('%Y-%m-%d %H:%M:%S')}"

@mirai_tool(description="在边缘设备本地终端打印一条消息")
def echo_message(msg: str) -> str:
    """
    让边缘设备在本地终端打印一条消息。
    参数:
        msg: 需要打印的文本内容
    """
    print(f"\n📢 [来自大脑的广播]: {msg}\n")
    return "消息已成功在边缘端打印。"
