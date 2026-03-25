# mirai/edge/client.py
import os
import shutil
import asyncio
import importlib
import sys
from dotenv import load_dotenv

# 引入我们刚才写的通用注册表
from mirai.utils.tool import TOOL_REGISTRY 

def init_workspace():
    """检测当前运行目录并初始化边缘端工作区"""
    current_dir = os.getcwd()
    tools_dir = os.path.join(current_dir, "mirai_tools")
    env_file = os.path.join(current_dir, ".env")

    # 1. 判断是否为老工作区
    if os.path.exists(tools_dir) and os.path.exists(env_file):
        print(f"✅ 检测到现有的 Mirai Edge 工作区: {current_dir}")
        return current_dir

    # 2. 安全锁：防止覆盖用户其他目录
    existing_files = [f for f in os.listdir(current_dir) if f != ".DS_Store"]
    if existing_files:
        print("❌ [拒绝初始化] 安全拦截：当前目录非空！")
        print("👉 解决办法：请新建一个空文件夹（例如 `mkdir my_edge_node`），进入该文件夹后再运行此命令。")
        return None

    print("✨ 这是一个新的空目录，正在为您初始化 Mirai Edge 环境...")
    
    # 3. 指向你现有的模板路径：mirai/edge/template
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, "template")

    if not os.path.exists(template_dir):
        print(f"❌ 严重错误: 找不到模板文件夹 {template_dir}")
        return None

    # 4. 执行模板拷贝
    for item_name in os.listdir(template_dir):
        source_path = os.path.join(template_dir, item_name)
        
        dest_name = item_name
        if item_name == "env.template":
            dest_name = ".env"
        elif item_name == "gitignore.template":
            dest_name = ".gitignore"
            
        dest_path = os.path.join(current_dir, dest_name)
        
        if os.path.isdir(source_path):
            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, dest_path)

    print(f"🎉 初始化完成！工作区已安全建在: {current_dir}")
    return current_dir

def scan_tools(workspace_dir: str):
    """扫描 mirai_tools 目录，动态加载所有工具"""
    tools_dir = os.path.join(workspace_dir, "mirai_tools")
    
    if workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)

    print("\n🔍 正在扫描可用工具...")
    for filename in os.listdir(tools_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"mirai_tools.{filename[:-3]}"
            try:
                importlib.import_module(module_name)
            except Exception as e:
                print(f"❌ 加载工具脚本 {filename} 时出错: {e}")

    print(f"✅ 扫描完成！当前节点共挂载 {len(TOOL_REGISTRY)} 个工具技能。")
    for name, tool_data in TOOL_REGISTRY.items():
        print(f"  - 🛠️ {name}: {tool_data['schema']['function']['description']}")

async def start_edge_client():
    """边缘端客户端主异步循环"""
    workspace_dir = init_workspace()
    if not workspace_dir:
        return
        
    # 1. 扫描工作区工具并注册到内存
    scan_tools(workspace_dir)
    
    # 2. 读取环境变量配置
    env_path = os.path.join(workspace_dir, ".env")
    load_dotenv(env_path)
    edge_name = os.getenv("EDGE_NAME", "Unknown_Edge")
    brain_url = os.getenv("BRAIN_URL", "ws://127.0.0.1:8000/ws/edge")
    
    print(f"\n📡 节点身份识别完毕: [{edge_name}]")
    print(f"📞 准备连接大脑: {brain_url} ... (待实现 WebSocket)")

if __name__ == "__main__":
    try:
        asyncio.run(start_edge_client())
    except KeyboardInterrupt:
        print("\n🔌 边缘端已安全断开连接。")