import inspect
from typing import Callable, Any, Dict


TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

def mirai_tool(description: str = None):
    def decorator(func: Callable):
        name = func.__name__
        doc = description or inspect.getdoc(func) or "No description provided."
        
        sig = inspect.signature(func)
        properties = {}
        required_params = []
        
        for param_name, param in sig.parameters.items():
            required_params.append(param_name)
            
            if param.annotation == inspect.Parameter.empty:
                print(f"[Mirai Tool Warning] Parameter '{param_name}' in tool '{name}' has no type annotation. Defaulting to string.")
                param_type = "string"
            else:
                if param.annotation == int: param_type = "integer"
                elif param.annotation == float: param_type = "number"
                elif param.annotation == bool: param_type = "boolean"
                else: param_type = "string"
                
            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter: {param_name}"
            }
        
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": doc.strip(),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_params
                }
            }
        }
        
        TOOL_REGISTRY[name] = {
            "schema": schema,
            "callable": func
        }
        
        return func
    return decorator
