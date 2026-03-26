import argparse
import subprocess
import urllib.request
import urllib.error
import sys
import os


SERVER_URL = os.getenv("MIRAI_SERVER_URL", "http://127.0.0.1:8000")

def is_server_running(url=f"{SERVER_URL}/health"):
    try:
        with urllib.request.urlopen(url) as response:
            return response.status == 200
    except urllib.error.URLError:
        return False

def main():
    parser = argparse.ArgumentParser(description="Mirai Agent Command Line Interface")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--server", action="store_true", help="Run the Mirai backend API server")
    group.add_argument("--ui", action="store_true", help="Open Streamlit Web UI")
    group.add_argument("--chat", action="store_true", help="Start chat in terminal")
    group.add_argument("--edge", action="store_true", help="Start Mirai Edge client")

    args = parser.parse_args()
    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        if args.server:
            api_path = os.path.join(base_dir, "core", "api.py")
            subprocess.run([sys.executable, api_path])
            return

        if args.ui:
            if not is_server_running():
                print("Mirai server is not running. Please start it with `mirai --server`.")
                sys.exit(1)

            print("Launching Streamlit Web UI...")
            ui_path = os.path.join(base_dir, "ui", "app.py")
            subprocess.run([sys.executable, "-m", "streamlit", "run", ui_path])
            
        elif args.chat:
            if not is_server_running():
                print("Mirai server is not running. Please start it with `mirai --server`.")
                sys.exit(1)

            chat_path = os.path.join(base_dir, "utils", "chat.py")
            subprocess.run([sys.executable, chat_path])
                
        elif args.edge:
            if not is_server_running():
                print("Mirai server is not running. Please start it with `mirai --server`.")
                sys.exit(1)

            edge_path = os.path.join(base_dir, "edge", "client.py")
            subprocess.run([sys.executable, edge_path])
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nShutting down Mirai.")

if __name__ == "__main__":
    main()
