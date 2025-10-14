from typing import Any, Dict, List
from pydantic import BaseModel, create_model
from langchain.tools import StructuredTool


def _map_json_type(prop: Dict[str, Any]):
    t = prop.get("type")
    if t == "string":
        return str
    if t == "integer":
        return int
    if t == "number":
        return float
    if t == "boolean":
        return bool
    if t == "array":
        item = prop.get("items", {})
        item_t = _map_json_type(item) or Any
        return List[item_t]  # type: ignore[index]
    return Any


def build_langchain_tools(tools_spec: Dict[str, Dict[str, Any]]) -> List[StructuredTool]:
    lc_tools: List[StructuredTool] = []

    for name, meta in tools_spec.items():
        schema = meta.get("schema", {})
        params = schema.get("parameters", {"type": "object", "properties": {}})
        properties: Dict[str, Dict[str, Any]] = params.get("properties", {})
        required: List[str] = params.get("required", [])

        fields: Dict[str, tuple] = {}
        for prop_name, prop_schema in properties.items():
            py_type = _map_json_type(prop_schema) or Any
            default = ... if prop_name in required else None
            fields[prop_name] = (py_type, default)

        if fields:
            ArgsModel = create_model(f"{name}_Args", **fields)  # type: ignore[var-annotated]
        else:
            class ArgsModel(BaseModel):
                pass

        underlying_fn = meta["function"]

        def _make_func(fn):
            def _wrapped(**kwargs):
                return fn(**kwargs)
            return _wrapped

        tool_func = _make_func(underlying_fn)

        lc_tool = StructuredTool.from_function(
            name=schema.get("name", name),
            description=schema.get("description", name),
            args_schema=ArgsModel,
            func=tool_func,
            return_direct=False,
        )
        lc_tools.append(lc_tool)

    return lc_tools


