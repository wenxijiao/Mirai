
def build_prompt(system: str, user: str, assistant: str) -> str:
    return f"{system}\n\nUser: {user}\n\nAssistant: {assistant}"

