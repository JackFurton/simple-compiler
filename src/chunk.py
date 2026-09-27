from typing import List, Any, Optional
from dataclasses import dataclass, field
try:
    from .opcodes import OpCode
except ImportError:
    from opcodes import OpCode


@dataclass
class Chunk:
    code: bytearray = field(default_factory=bytearray)
    constants: List[Any] = field(default_factory=list)
    lines: List[int] = field(default_factory=list)

    def write_byte(self, byte_val: int, line: int = 1) -> int:
        offset = len(self.code)
        self.code.append(byte_val & 0xFF)
        self.lines.append(line)
        return offset

    def write_opcode(self, opcode: OpCode, line: int = 1) -> int:
        return self.write_byte(int(opcode), line)

    def write_u16(self, val: int, line: int = 1) -> int:
        offset = len(self.code)
        self.write_byte((val >> 8) & 0xFF, line)
        self.write_byte(val & 0xFF, line)
        return offset

    def read_u16(self, offset: int) -> int:
        return (self.code[offset] << 8) | self.code[offset + 1]

    def patch_u16(self, offset: int, val: int) -> None:
        self.code[offset] = (val >> 8) & 0xFF
        self.code[offset + 1] = val & 0xFF

    def add_constant(self, value: Any) -> int:
        # Check if constant already exists for deduplication (for primitives)
        if isinstance(value, (int, float, str, bool)) or value is None:
            for idx, existing in enumerate(self.constants):
                if type(existing) is type(value) and existing == value:
                    return idx
        self.constants.append(value)
        return len(self.constants) - 1


@dataclass
class FunctionObject:
    name: str
    arity: int
    chunk: Chunk = field(default_factory=Chunk)

    def __repr__(self) -> str:
        return f"<fn {self.name}>" if self.name else "<script>"
