import importlib
import inspect
import os
import sys
import types
from functools import wraps
from typing import Any, Callable, Dict, get_args, get_origin

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}

def _annotation_to_schema(annotation: Any) -> Dict[str, Any]:
    if annotation == inspect.Parameter.empty:
        return {"type": "string"}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is not None:
        if origin in (list, tuple, set):
            item_schema = _annotation_to_schema(args[0]) if args else {"type": "string"}
            return {"type": "array", "items": item_schema}

        if origin is dict:
            value_schema = _annotation_to_schema(args[1]) if len(args) > 1 else {"type": "string"}
            return {"type": "object", "additionalProperties": value_schema}

        if origin in (types.UnionType, getattr(__import__("typing"), "Union")):
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return _annotation_to_schema(non_none_args[0])
            return {"type": "string"}

    if annotation == str:
        return {"type": "string"}
    if annotation == int:
        return {"type": "integer"}
    if annotation == float:
        return {"type": "number"}
    if annotation == bool:
        return {"type": "boolean"}
    if annotation in (list, tuple, set):
        return {"type": "array", "items": {"type": "string"}}
    if annotation == dict:
        return {"type": "object", "additionalProperties": {"type": "string"}}

    return {"type": "string"}

def mirai_tool(description: str = None):
    def decorator(func: Callable):
        name = func.__name__
        doc = description or inspect.getdoc(func) or "No description provided."
        
        sig = inspect.signature(func)
        properties = {}
        required_params = []
        
        for param_name, param in sig.parameters.items():
            if param.default == inspect.Parameter.empty:
                required_params.append(param_name)
            
            if param.annotation == inspect.Parameter.empty:
                print(f"[Mirai Tool Warning] Parameter '{param_name}' in tool '{name}' has no type annotation. Defaulting to string.")

            param_schema = _annotation_to_schema(param.annotation)
            param_schema["description"] = f"Parameter: {param_name}"
            properties[param_name] = param_schema
        
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

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        TOOL_REGISTRY[name] = {
            "schema": schema,
            "callable": wrapper 
        }
        
        return wrapper
    return decorator

def load_tools_from_directory(tools_dir: str, package_name: str):
    if not os.path.isdir(tools_dir):
        return []

    parent_dir = os.path.dirname(tools_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    imported_modules = []
    for filename in sorted(os.listdir(tools_dir)):
        if not filename.endswith(".py") or filename.startswith("__"):
            continue

        module_name = f"{package_name}.{filename[:-3]}"
        module = importlib.import_module(module_name)
        imported_modules.append(module.__name__)

    return imported_modules

async def execute_registered_tool(tool_name: str, arguments: Dict[str, Any]):
    if tool_name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{tool_name}' is not registered.")

    func = TOOL_REGISTRY[tool_name]["callable"]
    result = func(**arguments)
    if inspect.isawaitable(result):
        result = await result
    return result