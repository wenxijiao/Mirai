# mirai/edge/client.py
import os
import shutil
import asyncio
import importlib
import sys
import json
import websockets
from dotenv import load_dotenv

from mirai.utils.tool import TOOL_REGISTRY 

def init_workspace():
    """Inspect the current directory and initialize an edge workspace if needed."""
    current_dir = os.getcwd()
    tools_dir = os.path.join(current_dir, "mirai_tools")
    env_file = os.path.join(current_dir, ".env")

    if os.path.exists(tools_dir) and os.path.exists(env_file):
        print(f"Detected an existing Mirai Edge workspace: {current_dir}")
        return current_dir

    existing_files = [f for f in os.listdir(current_dir) if f != ".DS_Store"]
    if existing_files:
        print("[Initialization Blocked] The current directory is not empty.")
        print("Create a new empty folder (for example `mkdir my_edge_node`) and run this command there.")
        return None

    print("This is an empty directory. Initializing a new Mirai Edge workspace...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, "template")

    if not os.path.exists(template_dir):
        print(f"Fatal error: template directory not found: {template_dir}")
        return None

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

    print(f"Workspace initialization complete: {current_dir}")
    return current_dir

def scan_tools(workspace_dir: str):
    """Scan the mirai_tools directory and dynamically import available tools."""
    tools_dir = os.path.join(workspace_dir, "mirai_tools")
    
    if workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)

    print("\nScanning available tools...")
    for filename in os.listdir(tools_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"mirai_tools.{filename[:-3]}"
            try:
                importlib.import_module(module_name)
            except Exception as e:
                print(f"Failed to load tool script {filename}: {e}")

    print(f"Scan complete. This node mounted {len(TOOL_REGISTRY)} tools.")
    for name, tool_data in TOOL_REGISTRY.items():
        print(f"  - {name}: {tool_data['schema']['function']['description']}")

async def start_edge_client():
    """Main async loop for the edge client."""
    workspace_dir = init_workspace()
    if not workspace_dir:
        return
        
    scan_tools(workspace_dir)
    
    env_path = os.path.join(workspace_dir, ".env")
    load_dotenv(env_path)
    edge_name = os.getenv("EDGE_NAME", "Unknown_Edge")
    brain_url = os.getenv("BRAIN_URL", "ws://127.0.0.1:8000/ws/edge")
    
    print(f"\nEdge identity resolved: [{edge_name}]")
    
    tools_to_report = [data["schema"] for data in TOOL_REGISTRY.values()]
    
    print(f"Connecting to the server hub: {brain_url} ...")
    try:
        async with websockets.connect(brain_url) as websocket:
            print("Connected to the server. Reporting available tools...")
            
            register_msg = {
                "type": "register",
                "edge_name": edge_name,
                "tools": tools_to_report
            }
            await websocket.send(json.dumps(register_msg))
            
            print("Tool registration complete. Waiting for incoming commands...")
            
            while True:
                response = await websocket.recv()
                command = json.loads(response)
                print(f"\n🧠 [Incoming Command]: {command}")
                
                # 判断是否为工具调用指令
                if command.get("type") == "tool_call":
                    # 解析大脑传来的函数名、参数和唯一的任务ID
                    tool_name = command.get("name")
                    arguments = command.get("arguments", {})
                    call_id = command.get("call_id", "unknown")
                    
                    print(f"⚙️ Executing on edge: {tool_name} | Args: {arguments}")
                    
                    # 1. 去内存注册表里找真正的函数
                    if tool_name in TOOL_REGISTRY:
                        func = TOOL_REGISTRY[tool_name]["callable"]
                        try:
                            # 2. 判断函数是不是异步的，如果是，就 await 它！
                            import inspect
                            if inspect.iscoroutinefunction(func):
                                result = await func(**arguments)
                            else:
                                result = func(**arguments)
                                
                            print(f"✅ Success! Result: {result}")
                        except Exception as e:
                            result = f"Error executing tool: {str(e)}"
                            print(f"❌ Failed: {result}")
                    else:
                        result = f"Error: Tool '{tool_name}' not found on this edge node."
                        print(f"⚠️ Warning: {result}")
                        
                    # 3. 把执行结果打包，顺着网线发回给大脑
                    result_msg = {
                        "type": "tool_result",
                        "call_id": call_id,
                        "result": str(result) # 统一转成字符串，防止有无法 JSON 序列化的对象
                    }
                    await websocket.send(json.dumps(result_msg))
                    print("📤 Result reported to server.")
                
    except ConnectionRefusedError:
        print("Connection failed: the server is not running. Start it with `mirai --server` first.")
    except websockets.exceptions.ConnectionClosed:
        print("The server closed the connection.")
    except Exception as e:
        print(f"Unexpected network error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(start_edge_client())
    except KeyboardInterrupt:
        print("\nEdge client disconnected.")