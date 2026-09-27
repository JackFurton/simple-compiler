from typing import List, Any, Optional, Dict
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
    upvalue_count: int = 0
    chunk: Chunk = field(default_factory=Chunk)
    klass: Optional[Any] = None

    def __repr__(self) -> str:
        return f"<fn {self.name}>" if self.name else "<script>"


class ObjUpvalue:
    def __init__(self, location: Optional[int] = None):
        self.location: Optional[int] = location  # stack index if open, None if closed
        self.closed_val: Any = None

    def get(self, stack: List[Any]) -> Any:
        if self.location is not None:
            return stack[self.location]
        return self.closed_val

    def set(self, stack: List[Any], val: Any) -> None:
        if self.location is not None:
            stack[self.location] = val
        else:
            self.closed_val = val

    def __repr__(self) -> str:
        if self.location is not None:
            return f"<open upvalue at stack[{self.location}]>"
        return f"<closed upvalue: {repr(self.closed_val)}>"


@dataclass
class ClosureObject:
    function: FunctionObject
    upvalues: List[ObjUpvalue] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.function.name

    @property
    def arity(self) -> int:
        return self.function.arity

    @property
    def chunk(self) -> Chunk:
        return self.function.chunk

    @property
    def klass(self) -> Optional[Any]:
        return self.function.klass

    @klass.setter
    def klass(self, val: Any) -> None:
        self.function.klass = val

    def __repr__(self) -> str:
        return f"<fn {self.function.name}>" if self.function.name else "<script>"


@dataclass
class ClassObject:
    name: str
    methods: Dict[str, ClosureObject] = field(default_factory=dict)
    superclass: Optional['ClassObject'] = None

    def find_method(self, name: str) -> Optional[ClosureObject]:
        if name in self.methods:
            return self.methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def __repr__(self) -> str:
        return f"<class {self.name}>"


@dataclass
class InstanceObject:
    klass: ClassObject
    fields: Dict[str, Any] = field(default_factory=dict)

    def get_field(self, name: str) -> Any:
        return self.fields.get(name)

    def set_field(self, name: str, value: Any) -> None:
        self.fields[name] = value

    def __repr__(self) -> str:
        return f"<instance of {self.klass.name}>"


@dataclass
class BoundMethod:
    receiver: InstanceObject
    method: ClosureObject

    @property
    def name(self) -> str:
        return self.method.name

    @property
    def arity(self) -> int:
        return self.method.arity

    def __repr__(self) -> str:
        return f"<bound method {self.method.name} of {self.receiver}>"
