
# from ollama import chat

# stream = chat(
#   model='qwen3.5:9b',
#   messages=[{'role': 'user', 'content': 'What is the capital of France?, please output the answer concisely and directly'}],
#   think=False,
#   stream=True,
# )

# in_thinking = False

# for chunk in stream:
#   if chunk.message.thinking and not in_thinking:
#     in_thinking = True
#     print('Thinking:\n', end='')

#   if chunk.message.thinking:
#     print(chunk.message.thinking, end='')
#   elif chunk.message.content:
#     if in_thinking:
#       print('\n\nAnswer:\n', end='')
#       in_thinking = False
#     print(chunk.message.content, end='')

# import requests

# def test_stream(prompt):
#     url = "http://127.0.0.1:8000/chat"
#     params = {"prompt": prompt}
    
#     with requests.post(url, params=params, stream=True) as r:
#         print("AI: \n")
#         for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
#             if chunk:
#                 print(chunk, end="", flush=True)
#         print("\n")

# if __name__ == "__main__":
#     while True:
#         user_input = input("You(Input 'exit', 'quit' or 'q' to exit): ")
#         if user_input.lower() in ['exit', 'quit', 'q']:
#             break
#         test_stream(user_input)

# from datetime import datetime

# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S %A"))
# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S %A"))

def test():
    print("This is a test function for Mirai.")

m = test()
print(m)
