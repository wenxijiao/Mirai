# mirai/utils/chat.py
import os
import requests

SERVER_URL = os.getenv("MIRAI_SERVER_URL", "http://127.0.0.1:8000")
DEFAULT_SESSION_ID = "chat_default"


def chat_stream(prompt, session_id=DEFAULT_SESSION_ID):
    url = f"{SERVER_URL}/chat"
    payload = {"prompt": prompt, "session_id": session_id}
    
    print("Mirai: ", end="", flush=True)
    try:
        with requests.post(url, json=payload, stream=True) as r:
            r.raise_for_status() 
            
            for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    print(chunk, end="", flush=True)
            print("\n")
            
    except requests.exceptions.ConnectionError:
        print("\n[Error] Cannot connect to the server. Make sure the backend is running and ready.\n")
    except Exception as e:
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
        