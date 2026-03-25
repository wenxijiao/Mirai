import inspect
from typing import Callable, Any, Dict


TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

def mirai_tool(description: str = None):
    def decorator(func: Callable):
        name = func.__name__
        doc = description or inspect.getdoc(func) or "未提供功能描述"
        
        sig = inspect.signature(func)
        properties = {}
        required_params = []
        
        for param_name, param in sig.parameters.items():
            required_params.append(param_name)
            
            if param.annotation == inspect.Parameter.empty:
                print(f"⚠️ [Mirai Tool 警告] 工具 '{name}' 的参数 '{param_name}' 未标注类型，已默认设为 string。")
                param_type = "string"
            else:
                if param.annotation == int: param_type = "integer"
                elif param.annotation == float: param_type = "number"
                elif param.annotation == bool: param_type = "boolean"
                else: param_type = "string"
                
            properties[param_name] = {
                "type": param_type,
                "description": f"参数 {param_name}"
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
