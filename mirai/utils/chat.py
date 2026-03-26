# mirai/utils/chat.py
import json
import os
import requests

SERVER_URL = os.getenv("MIRAI_SERVER_URL", "http://127.0.0.1:8000")
DEFAULT_SESSION_ID = "chat_default"


def chat_stream(prompt, session_id=DEFAULT_SESSION_ID):
    url = f"{SERVER_URL}/chat"
    payload = {"prompt": prompt, "session_id": session_id}

    printed_text = False
    try:
        with requests.post(url, json=payload, stream=True) as r:
            r.raise_for_status()

            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue

                event = json.loads(line)
                event_type = event.get("type")

                if event_type == "text":
                    if not printed_text:
                        print("Mirai: ", end="", flush=True)
                        printed_text = True
                    print(event.get("content", ""), end="", flush=True)
                elif event_type == "tool_status":
                    if printed_text:
                        print()
                        printed_text = False
                    print(f"[Tool] {event.get('content', '')}")
                elif event_type == "error":
                    if printed_text:
                        print()
                    print(f"[Error] {event.get('content', 'Unknown backend error.')}")

            print("\n")
            
    except requests.exceptions.ConnectionError:
        print("\n[Error] Cannot connect to the server. Make sure the backend is running and ready.\n")
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"\n[Error] Something unexpected happened: {e}\n")

if __name__ == "__main__":
    print("Mirai terminal chat started. Type 'exit' or 'q' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
        if user_input.strip() == "": 
            continue
            
        chat_stream(user_input)
        