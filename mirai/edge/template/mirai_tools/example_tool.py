from datetime import datetime
from mirai.utils.tool import mirai_tool 

@mirai_tool(description="Get the current local time on the edge device.")
def get_device_time() -> str:
    now = datetime.now()
    return f"Current edge device time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

@mirai_tool(description="Print a message in the local terminal of the edge device.")
def echo_message(msg: str) -> str:
    """
    Print a message in the local terminal on the edge device.
    Args:
        msg: The text content to print.
    """
    print(f"\n[Broadcast from server] {msg}\n")
    return "The message was printed successfully on the edge device."
