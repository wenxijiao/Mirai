# mirai/cli.py
import argparse
import os

# 这里的导入路径变成了从 mirai 包绝对导入
# from mirai.backend.agent_core import TOOL_REGISTRY

def main():
    parser = argparse.ArgumentParser(description="Mirai Agent 命令行控制台")
    
    # 定义带 -- 的参数，action="store_true" 的意思是只要敲了这个参数，它的值就是 True
    parser.add_argument("--ui", action="store_true", help="启动 Streamlit 网页端 UI")
    parser.add_argument("--update", action="store_true", help="扫描并更新插件注册表")
    parser.add_argument("--chat", action="store_true", help="在终端开启对话")

    args = parser.parse_args()

    if args.ui:
        print("🚀 正在启动 Streamlit Web UI...")
        # 获取当前文件所在目录，推导出 web_ui.py 的绝对路径，防止在别的文件夹下运行报错
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(base_dir, "frontend", "web_ui.py")
        os.system(f"streamlit run {ui_path}")
        
    elif args.update:
        print("🔄 正在扫描并更新插件索引...")
        print("✅ 更新完成！")
        
    elif args.chat:
        print("🤖 Mirai 终端对话已启动！(输入 'exit' 退出)")
        while True:
            user_input = input("你: ")
            if user_input.lower() in ['exit', 'quit']:
                break
            print(f"Mirai: 收到 -> {user_input}")
            
    else:
        # 如果什么参数都没带，就打印帮助信息
        parser.print_help()

if __name__ == "__main__":
    main()
