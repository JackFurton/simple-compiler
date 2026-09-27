import time
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass

try:
    from .opcodes import OpCode
    from .chunk import Chunk, FunctionObject, ClosureObject, ObjUpvalue, ClassObject, InstanceObject, BoundMethod
    from .stdlib import get_stdlib_functions, get_stdlib_constants
except ImportError:
    from opcodes import OpCode
    from chunk import Chunk, FunctionObject, ClosureObject, ObjUpvalue, ClassObject, InstanceObject, BoundMethod
    from stdlib import get_stdlib_functions, get_stdlib_constants


class VMError(Exception):
    def __init__(self, message: str, stack_trace: Optional[List[str]] = None):
        self.message = message
        self.stack_trace = stack_trace or []
        formatted = message
        if self.stack_trace:
            formatted += "\n" + "\n".join(f"  {line}" for line in self.stack_trace)
        super().__init__(formatted)


@dataclass
class CallFrame:
    closure: ClosureObject
    ip: int = 0
    slots: int = 0

    def __init__(self, closure: Optional[ClosureObject] = None, function: Optional[FunctionObject] = None, ip: int = 0, slots: int = 0):
        if closure is not None:
            self.closure = closure
        elif function is not None:
            self.closure = ClosureObject(function=function)
        else:
            raise ValueError("CallFrame requires either closure or function")
        self.ip = ip
        self.slots = slots

    @property
    def function(self) -> FunctionObject:
        return self.closure.function

    def read_byte(self) -> int:
        byte_val = self.function.chunk.code[self.ip]
        self.ip += 1
        return byte_val

    def read_u16(self) -> int:
        val = self.function.chunk.read_u16(self.ip)
        self.ip += 2
        return val

    def read_constant(self) -> Any:
        idx = self.read_u16()
        return self.function.chunk.constants[idx]


class VM:
    MAX_FRAMES = 1000

    def __init__(self, output_callback: Optional[Callable[[Any], None]] = None):
        self.output_callback = output_callback or print
        self.stack: List[Any] = []
        self.frames: List[CallFrame] = []
        self.open_upvalues: List[ObjUpvalue] = []
        self.globals: Dict[str, Any] = self._setup_globals()
        self.builtins: Dict[str, Callable] = self._setup_builtins()

    def _setup_globals(self) -> Dict[str, Any]:
        return get_stdlib_constants().copy()

    def _setup_builtins(self) -> Dict[str, Callable]:
        builtins = {
            'clock': time.time,
            'len': lambda obj: len(obj) if hasattr(obj, '__len__') else 0,
            'str': str,
            'int': lambda v: int(v) if v is not None else 0,
            'float': lambda v: float(v) if v is not None else 0.0,
            'type': self._builtin_type,
            'print': self._builtin_print,
            'append': lambda lst, val: lst.append(val),
            'pop': lambda lst, *args: lst.pop(*args) if lst else None,
            'keys': lambda d: list(d.keys()) if isinstance(d, dict) else [],
            'values': lambda d: list(d.values()) if isinstance(d, dict) else [],
        }
        builtins.update(get_stdlib_functions())
        return builtins

    def _builtin_type(self, val: Any) -> str:
        if val is None:
            return "nil"
        if isinstance(val, bool):
            return "bool"
        if isinstance(val, (int, float)):
            return "number"
        if isinstance(val, str):
            return "string"
        if isinstance(val, list):
            return "list"
        if isinstance(val, dict):
            return "dict"
        if isinstance(val, ClassObject):
            return "class"
        if isinstance(val, InstanceObject):
            return "instance"
        if isinstance(val, BoundMethod):
            return "method"
        if isinstance(val, (FunctionObject, ClosureObject)) or callable(val):
            return "function"
        return type(val).__name__

    def _builtin_print(self, *args) -> None:
        if len(args) == 1:
            self.output_callback(args[0])
        else:
            self.output_callback(" ".join(str(a) for a in args))
        return None

    def push(self, value: Any) -> None:
        self.stack.append(value)

    def pop(self) -> Any:
        if not self.stack:
            self.runtime_error("Stack underflow")
        return self.stack.pop()

    def peek(self, distance: int = 0) -> Any:
        idx = len(self.stack) - 1 - distance
        if idx < 0 or idx >= len(self.stack):
            self.runtime_error("Invalid stack peek")
        return self.stack[idx]

    def is_truthy(self, value: Any) -> bool:
        return bool(value)

    def runtime_error(self, message: str) -> None:
        trace = []
        for frame in reversed(self.frames):
            fn_name = frame.function.name or "<script>"
            # ip points to next instruction, so previous byte is at ip - 1
            line = 1
            if frame.function.chunk.lines and frame.ip > 0:
                line_idx = min(frame.ip - 1, len(frame.function.chunk.lines) - 1)
                line = frame.function.chunk.lines[line_idx]
            trace.append(f"[line {line}] in {fn_name}()")
        raise VMError(message, trace)

    def capture_upvalue(self, location: int) -> ObjUpvalue:
        for upval in self.open_upvalues:
            if upval.location == location:
                return upval
        created = ObjUpvalue(location)
        self.open_upvalues.append(created)
        return created

    def close_upvalues(self, last_slot: int) -> None:
        i = 0
        while i < len(self.open_upvalues):
            upval = self.open_upvalues[i]
            if upval.location is not None and upval.location >= last_slot:
                upval.closed_val = self.stack[upval.location]
                upval.location = None
                self.open_upvalues.pop(i)
            else:
                i += 1

    def call_value(self, callee: Any, arg_count: int) -> None:
        if isinstance(callee, (ClosureObject, FunctionObject)):
            closure = callee if isinstance(callee, ClosureObject) else ClosureObject(function=callee)
            fn = closure.function
            if arg_count != fn.arity:
                self.runtime_error(f"Function '{fn.name}' expected {fn.arity} arguments but got {arg_count}")

            if len(self.frames) >= self.MAX_FRAMES:
                self.runtime_error("Stack overflow: maximum recursion depth exceeded")

            slots = len(self.stack) - arg_count - 1
            new_frame = CallFrame(closure=closure, ip=0, slots=slots)
            self.frames.append(new_frame)

        elif isinstance(callee, ClassObject):
            instance = InstanceObject(klass=callee)
            init_method = callee.find_method("init")
            if init_method is not None:
                if arg_count != init_method.arity:
                    self.runtime_error(f"Class '{callee.name}' constructor expected {init_method.arity} arguments but got {arg_count}")

                if len(self.frames) >= self.MAX_FRAMES:
                    self.runtime_error("Stack overflow: maximum recursion depth exceeded")

                slots = len(self.stack) - arg_count - 1
                self.stack[slots] = instance
                new_frame = CallFrame(closure=init_method, ip=0, slots=slots)
                self.frames.append(new_frame)
            else:
                if arg_count != 0:
                    self.runtime_error(f"Class '{callee.name}' takes no constructor arguments, got {arg_count}")
                self.pop()  # pop class
                self.push(instance)

        elif isinstance(callee, BoundMethod):
            closure = callee.method
            fn = closure.function
            if arg_count != fn.arity:
                self.runtime_error(f"Method '{fn.name}' expected {fn.arity} arguments but got {arg_count}")

            if len(self.frames) >= self.MAX_FRAMES:
                self.runtime_error("Stack overflow: maximum recursion depth exceeded")

            slots = len(self.stack) - arg_count - 1
            self.stack[slots] = callee.receiver
            new_frame = CallFrame(closure=closure, ip=0, slots=slots)
            self.frames.append(new_frame)

        elif callable(callee):
            # Built-in or host Python function
            args = []
            for _ in range(arg_count):
                args.append(self.pop())
            args.reverse()
            self.pop()  # Pop the callee function itself
            try:
                result = callee(*args)
            except Exception as e:
                self.runtime_error(f"Error in native call: {e}")
            self.push(result)

        else:
            self.runtime_error(f"Can only call functions, got {type(callee).__name__}")

    def interpret(self, main_function: Union[FunctionObject, ClosureObject]) -> Any:
        self.stack.clear()
        self.frames.clear()
        self.open_upvalues.clear()
        if isinstance(main_function, ClosureObject):
            main_closure = main_function
        else:
            main_closure = ClosureObject(function=main_function)
        self.push(main_closure)
        root_frame = CallFrame(closure=main_closure, ip=0, slots=0)
        self.frames.append(root_frame)
        return self.run()

    def run(self) -> Any:
        while self.frames:
            frame = self.frames[-1]
            if frame.ip >= len(frame.function.chunk.code):
                self.frames.pop()
                continue

            byte_val = frame.read_byte()
            try:
                opcode = OpCode(byte_val)
            except ValueError:
                self.runtime_error(f"Unknown opcode byte: {byte_val}")

            if opcode == OpCode.OP_CONSTANT:
                constant = frame.read_constant()
                self.push(constant)

            elif opcode == OpCode.OP_NIL:
                self.push(None)

            elif opcode == OpCode.OP_TRUE:
                self.push(True)

            elif opcode == OpCode.OP_FALSE:
                self.push(False)

            elif opcode == OpCode.OP_POP:
                self.pop()

            elif opcode == OpCode.OP_DUP:
                self.push(self.peek(0))

            elif opcode == OpCode.OP_GET_LOCAL:
                slot = frame.read_u16()
                self.push(self.stack[frame.slots + slot])

            elif opcode == OpCode.OP_SET_LOCAL:
                slot = frame.read_u16()
                self.stack[frame.slots + slot] = self.peek(0)

            elif opcode == OpCode.OP_GET_UPVALUE:
                slot = frame.read_u16()
                upval = frame.closure.upvalues[slot]
                self.push(upval.get(self.stack))

            elif opcode == OpCode.OP_SET_UPVALUE:
                slot = frame.read_u16()
                upval = frame.closure.upvalues[slot]
                upval.set(self.stack, self.peek(0))

            elif opcode == OpCode.OP_CLOSE_UPVALUE:
                self.close_upvalues(len(self.stack) - 1)
                self.pop()

            elif opcode == OpCode.OP_DEFINE_GLOBAL:
                name = frame.read_constant()
                self.globals[name] = self.pop()

            elif opcode == OpCode.OP_GET_GLOBAL:
                name = frame.read_constant()
                if name in self.globals:
                    self.push(self.globals[name])
                elif name in self.builtins:
                    self.push(self.builtins[name])
                else:
                    self.runtime_error(f"Undefined variable '{name}'")

            elif opcode == OpCode.OP_SET_GLOBAL:
                name = frame.read_constant()
                if name in self.builtins and name not in self.globals:
                    self.runtime_error(f"Cannot overwrite built-in '{name}'")
                self.globals[name] = self.peek(0)

            elif opcode == OpCode.OP_EQUAL:
                b = self.pop()
                a = self.pop()
                self.push(a == b)

            elif opcode == OpCode.OP_GREATER:
                b = self.pop()
                a = self.pop()
                if not (isinstance(a, (int, float, str)) and isinstance(b, (int, float, str)) and type(a) == type(b)):
                    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
                        self.runtime_error(f"Cannot compare '{type(a).__name__}' and '{type(b).__name__}'")
                self.push(a > b)

            elif opcode == OpCode.OP_LESS:
                b = self.pop()
                a = self.pop()
                if not (isinstance(a, (int, float, str)) and isinstance(b, (int, float, str)) and type(a) == type(b)):
                    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
                        self.runtime_error(f"Cannot compare '{type(a).__name__}' and '{type(b).__name__}'")
                self.push(a < b)

            elif opcode == OpCode.OP_ADD:
                b = self.pop()
                a = self.pop()
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    self.push(a + b)
                elif isinstance(a, str) or isinstance(b, str):
                    self.push(str(a) + str(b))
                else:
                    self.runtime_error(f"Cannot add '{type(a).__name__}' and '{type(b).__name__}'")

            elif opcode == OpCode.OP_SUB:
                b = self.pop()
                a = self.pop()
                if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
                    self.runtime_error(f"Operands must be numbers, got '{type(a).__name__}' and '{type(b).__name__}'")
                self.push(a - b)

            elif opcode == OpCode.OP_MUL:
                b = self.pop()
                a = self.pop()
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    self.push(a * b)
                elif isinstance(a, str) and isinstance(b, int):
                    self.push(a * b)
                else:
                    self.runtime_error(f"Cannot multiply '{type(a).__name__}' and '{type(b).__name__}'")

            elif opcode == OpCode.OP_DIV:
                b = self.pop()
                a = self.pop()
                if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
                    self.runtime_error(f"Operands must be numbers, got '{type(a).__name__}' and '{type(b).__name__}'")
                if b == 0:
                    self.runtime_error("Division by zero")
                self.push(a / b)

            elif opcode == OpCode.OP_MOD:
                b = self.pop()
                a = self.pop()
                if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
                    self.runtime_error(f"Operands must be numbers, got '{type(a).__name__}' and '{type(b).__name__}'")
                if b == 0:
                    self.runtime_error("Modulo by zero")
                self.push(a % b)

            elif opcode == OpCode.OP_NOT:
                self.push(not self.is_truthy(self.pop()))

            elif opcode == OpCode.OP_NEGATE:
                val = self.pop()
                if not isinstance(val, (int, float)):
                    self.runtime_error(f"Operand must be a number, got '{type(val).__name__}'")
                self.push(-val)

            elif opcode == OpCode.OP_PRINT:
                val = self.pop()
                self.output_callback(val)

            elif opcode == OpCode.OP_JUMP:
                offset = frame.read_u16()
                frame.ip += offset

            elif opcode == OpCode.OP_JUMP_IF_FALSE:
                offset = frame.read_u16()
                if not self.is_truthy(self.peek(0)):
                    frame.ip += offset

            elif opcode == OpCode.OP_LOOP:
                offset = frame.read_u16()
                frame.ip -= offset

            elif opcode == OpCode.OP_CLOSURE:
                const_idx = frame.read_u16()
                fn = frame.function.chunk.constants[const_idx]
                closure = ClosureObject(function=fn)
                for _ in range(fn.upvalue_count):
                    is_local = frame.read_byte()
                    index = frame.read_u16()
                    if is_local:
                        closure.upvalues.append(self.capture_upvalue(frame.slots + index))
                    else:
                        closure.upvalues.append(frame.closure.upvalues[index])
                self.push(closure)

            elif opcode == OpCode.OP_CALL:
                arg_count = frame.read_byte()
                self.call_value(self.peek(arg_count), arg_count)

            elif opcode == OpCode.OP_CLASS:
                name = frame.read_constant()
                self.push(ClassObject(name=name))

            elif opcode == OpCode.OP_INHERIT:
                super_val = self.pop()
                sub_val = self.peek(0)
                if not isinstance(super_val, ClassObject):
                    self.runtime_error(f"Superclass must be a class, got {type(super_val).__name__}")
                if super_val is sub_val:
                    self.runtime_error("A class cannot inherit from itself")
                sub_val.superclass = super_val

            elif opcode == OpCode.OP_METHOD:
                name = frame.read_constant()
                method_closure = self.pop()
                klass = self.peek(0)
                if not isinstance(klass, ClassObject):
                    self.runtime_error("OP_METHOD called without class on stack")
                klass.methods[name] = method_closure
                method_closure.function.klass = klass

            elif opcode == OpCode.OP_GET_PROPERTY:
                name = frame.read_constant()
                target = self.pop()
                if not isinstance(target, InstanceObject):
                    self.runtime_error(f"Only instances have properties, got {type(target).__name__}")
                if name in target.fields:
                    self.push(target.fields[name])
                else:
                    method = target.klass.find_method(name)
                    if method is not None:
                        self.push(BoundMethod(receiver=target, method=method))
                    else:
                        self.runtime_error(f"Undefined property '{name}' on instance of {target.klass.name}")

            elif opcode == OpCode.OP_SET_PROPERTY:
                name = frame.read_constant()
                val = self.pop()
                target = self.pop()
                if not isinstance(target, InstanceObject):
                    self.runtime_error(f"Only instances have fields, got {type(target).__name__}")
                target.set_field(name, val)
                self.push(val)

            elif opcode == OpCode.OP_GET_SUPER:
                name = frame.read_constant()
                receiver = self.pop()
                if not isinstance(receiver, InstanceObject):
                    self.runtime_error("Invalid receiver for super call")
                current_klass = frame.function.klass
                if current_klass is None or current_klass.superclass is None:
                    self.runtime_error("Cannot resolve superclass for super call")
                method = current_klass.superclass.find_method(name)
                if method is None:
                    self.runtime_error(f"Undefined property '{name}' in superclass '{current_klass.superclass.name}'")
                self.push(BoundMethod(receiver=receiver, method=method))

            elif opcode == OpCode.OP_BUILD_LIST:
                count = frame.read_u16()
                elements = []
                for _ in range(count):
                    elements.append(self.pop())
                elements.reverse()
                self.push(elements)

            elif opcode == OpCode.OP_BUILD_MAP:
                count = frame.read_u16()
                pairs = []
                for _ in range(count):
                    val = self.pop()
                    key = self.pop()
                    pairs.append((key, val))
                pairs.reverse()
                d = {k: v for k, v in pairs}
                self.push(d)

            elif opcode == OpCode.OP_GET_INDEX:
                index = self.pop()
                target = self.pop()
                try:
                    self.push(target[index])
                except (IndexError, KeyError, TypeError) as e:
                    self.runtime_error(f"Index error: {e}")

            elif opcode == OpCode.OP_SET_INDEX:
                val = self.pop()
                index = self.pop()
                target = self.pop()
                try:
                    target[index] = val
                    self.push(val)
                except (IndexError, KeyError, TypeError) as e:
                    self.runtime_error(f"Index assignment error: {e}")

            elif opcode == OpCode.OP_RETURN:
                result = self.pop()
                self.close_upvalues(frame.slots)
                prev_frame = self.frames.pop()
                if not self.frames:
                    return result
                # Reset stack to the base of the returning function frame
                self.stack = self.stack[:prev_frame.slots]
                self.push(result)

        return None
