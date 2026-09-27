from typing import Tuple, List, Optional
try:
    from .opcodes import OpCode
    from .chunk import Chunk, FunctionObject
except ImportError:
    from opcodes import OpCode
    from chunk import Chunk, FunctionObject


def disassemble_chunk(chunk: Chunk, name: str) -> str:
    lines: List[str] = [f"== {name} =="]
    offset = 0
    nested_functions: List[Tuple[str, Chunk]] = []

    while offset < len(chunk.code):
        disasm_line, offset, nested = disassemble_instruction(chunk, offset)
        lines.append(disasm_line)
        if nested:
            nested_functions.append(nested)

    for fn_name, fn_chunk in nested_functions:
        lines.append("")
        lines.append(disassemble_chunk(fn_chunk, fn_name))

    return "\n".join(lines)


def disassemble_instruction(chunk: Chunk, offset: int) -> Tuple[str, int, Optional[Tuple[str, Chunk]]]:
    line_num = chunk.lines[offset]
    prev_line = chunk.lines[offset - 1] if offset > 0 else -1
    line_str = f"{line_num:4d}" if line_num != prev_line else "   |"

    byte_val = chunk.code[offset]
    try:
        opcode = OpCode(byte_val)
    except ValueError:
        return f"{offset:04d} {line_str} UNKNOWN_OPCODE {byte_val}", offset + 1, None

    nested_fn = None

    if opcode == OpCode.OP_CONSTANT:
        const_idx = chunk.read_u16(offset + 1)
        val = chunk.constants[const_idx]
        val_str = repr(val)
        if isinstance(val, FunctionObject):
            nested_fn = (val.name or "<anonymous>", val.chunk)
        return f"{offset:04d} {line_str} {opcode.name:<18} {const_idx:4d} ({val_str})", offset + 3, nested_fn

    elif opcode in (OpCode.OP_DEFINE_GLOBAL, OpCode.OP_GET_GLOBAL, OpCode.OP_SET_GLOBAL):
        const_idx = chunk.read_u16(offset + 1)
        name = chunk.constants[const_idx]
        return f"{offset:04d} {line_str} {opcode.name:<18} {const_idx:4d} ('{name}')", offset + 3, None

    elif opcode in (OpCode.OP_GET_LOCAL, OpCode.OP_SET_LOCAL):
        slot = chunk.read_u16(offset + 1)
        return f"{offset:04d} {line_str} {opcode.name:<18} slot {slot}", offset + 3, None

    elif opcode in (OpCode.OP_JUMP, OpCode.OP_JUMP_IF_FALSE):
        jump_offset = chunk.read_u16(offset + 1)
        target = offset + 3 + jump_offset
        return f"{offset:04d} {line_str} {opcode.name:<18} -> {target:04d} (+{jump_offset})", offset + 3, None

    elif opcode == OpCode.OP_LOOP:
        jump_offset = chunk.read_u16(offset + 1)
        target = offset + 3 - jump_offset
        return f"{offset:04d} {line_str} {opcode.name:<18} -> {target:04d} (-{jump_offset})", offset + 3, None

    elif opcode in (OpCode.OP_BUILD_LIST, OpCode.OP_BUILD_MAP):
        count = chunk.read_u16(offset + 1)
        return f"{offset:04d} {line_str} {opcode.name:<18} count {count}", offset + 3, None

    elif opcode == OpCode.OP_CALL:
        arg_count = chunk.code[offset + 1]
        return f"{offset:04d} {line_str} {opcode.name:<18} args {arg_count}", offset + 2, None

    else:
        return f"{offset:04d} {line_str} {opcode.name}", offset + 1, None
