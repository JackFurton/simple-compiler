import json
from typing import Any, Dict
try:
    from .chunk import Chunk, FunctionObject
except ImportError:
    from chunk import Chunk, FunctionObject

MAGIC_HEADER = b"LANGC\x01\x00"


def function_to_dict(fn: FunctionObject) -> Dict[str, Any]:
    serialized_constants = []
    for c in fn.chunk.constants:
        if isinstance(c, FunctionObject):
            serialized_constants.append({
                "type": "function",
                "value": function_to_dict(c)
            })
        elif isinstance(c, (int, float)):
            serialized_constants.append({
                "type": "number",
                "value": c
            })
        elif isinstance(c, str):
            serialized_constants.append({
                "type": "string",
                "value": c
            })
        elif isinstance(c, bool):
            serialized_constants.append({
                "type": "bool",
                "value": c
            })
        elif c is None:
            serialized_constants.append({
                "type": "nil",
                "value": None
            })
        else:
            raise ValueError(f"Cannot serialize constant of type {type(c).__name__}")

    return {
        "name": fn.name,
        "arity": fn.arity,
        "upvalue_count": fn.upvalue_count,
        "code": list(fn.chunk.code),
        "lines": fn.chunk.lines,
        "constants": serialized_constants,
        "debug_locals": {str(k): v for k, v in fn.debug_locals.items()}
    }


def dict_to_function(data: Dict[str, Any]) -> FunctionObject:
    fn = FunctionObject(
        name=data["name"],
        arity=data["arity"],
        upvalue_count=data.get("upvalue_count", 0),
        debug_locals={int(k): v for k, v in data.get("debug_locals", {}).items()}
    )
    chunk = fn.chunk
    chunk.code = bytearray(data["code"])
    chunk.lines = list(data["lines"])

    constants = []
    for c in data["constants"]:
        c_type = c["type"]
        val = c["value"]
        if c_type == "function":
            constants.append(dict_to_function(val))
        elif c_type in ("number", "string", "bool", "nil"):
            constants.append(val)
        else:
            raise ValueError(f"Unknown serialized constant type: {c_type}")

    chunk.constants = constants
    return fn


def serialize_bytecode(fn: FunctionObject) -> bytes:
    payload = json.dumps(function_to_dict(fn), separators=(',', ':')).encode('utf-8')
    return MAGIC_HEADER + payload


def deserialize_bytecode(data: bytes) -> FunctionObject:
    if not data.startswith(MAGIC_HEADER):
        raise ValueError("Invalid bytecode file: missing or incorrect LANGC magic header")

    payload = data[len(MAGIC_HEADER):].decode('utf-8')
    data_dict = json.loads(payload)
    return dict_to_function(data_dict)
