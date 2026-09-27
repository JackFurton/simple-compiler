import sys
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass

try:
    from .opcodes import OpCode
    from .chunk import Chunk, FunctionObject, ClosureObject, InstanceObject, ClassObject, BoundMethod
    from .disassembler import disassemble_instruction
except ImportError:
    from opcodes import OpCode
    from chunk import Chunk, FunctionObject, ClosureObject, InstanceObject, ClassObject, BoundMethod
    from disassembler import disassemble_instruction


class DebuggerExit(Exception):
    """Raised to cleanly exit program execution from the debugger."""
    pass


@dataclass
class Breakpoint:
    id: int
    bp_type: str  # "line" or "function"
    target: Union[int, str]  # line number or function name
    enabled: bool = True
    hit_count: int = 0

    def __repr__(self) -> str:
        state = "enabled" if self.enabled else "disabled"
        if self.bp_type == "line":
            return f"Breakpoint #{self.id} at line {self.target} ({state}, hit {self.hit_count} times)"
        return f"Breakpoint #{self.id} at function {self.target}() ({state}, hit {self.hit_count} times)"


class Debugger:
    def __init__(
        self,
        vm: Any,
        source: Optional[str] = None,
        filename: str = "<source>",
        input_fn: Optional[Callable[[str], str]] = None,
        output_fn: Optional[Callable[[str], None]] = None,
        pause_at_start: bool = False
    ):
        self.vm = vm
        self.source = source or ""
        self.source_lines = self.source.splitlines() if self.source else []
        self.filename = filename
        self.input_fn = input_fn or input
        self.output_fn = output_fn or print
        self.pause_at_start = pause_at_start
        self.has_started = False

        self.breakpoints: Dict[int, Breakpoint] = {}
        self.next_bp_id = 1
        self.step_mode = "continue"  # "continue", "step", "next", "stepi", "finish"
        self.target_depth = 0
        self.last_line: Optional[int] = None
        self.last_frame: Optional[Any] = None
        self.frame_lines: Dict[int, int] = {}
        self.triggered_fn_frames: set = set()
        self.last_command = ""
        self.is_paused = False

    def add_line_breakpoint(self, line: int) -> Breakpoint:
        bp = Breakpoint(id=self.next_bp_id, bp_type="line", target=line)
        self.breakpoints[self.next_bp_id] = bp
        self.next_bp_id += 1
        return bp

    def add_function_breakpoint(self, fn_name: str) -> Breakpoint:
        bp = Breakpoint(id=self.next_bp_id, bp_type="function", target=fn_name)
        self.breakpoints[self.next_bp_id] = bp
        self.next_bp_id += 1
        return bp

    def remove_breakpoint(self, bp_id: int) -> bool:
        if bp_id in self.breakpoints:
            del self.breakpoints[bp_id]
            return True
        return False

    def clear_breakpoints(self) -> None:
        self.breakpoints.clear()

    def get_current_line(self, frame: Any) -> int:
        if frame.ip < len(frame.function.chunk.lines):
            return frame.function.chunk.lines[frame.ip]
        return 1

    def print_line(self, msg: str = "") -> None:
        self.output_fn(msg)

    def hook(self, vm: Any, frame: Any) -> None:
        if self.pause_at_start and not self.has_started:
            self.has_started = True
            current_line = self.get_current_line(frame)
            self.last_line = current_line
            self.last_frame = frame
            self.pause(frame, "Paused at program entry")
            return

        current_line = self.get_current_line(frame)
        current_fn = frame.function.name or "<script>"
        current_depth = len(vm.frames)

        frame_key = id(frame)
        prev_line_for_frame = self.frame_lines.get(frame_key)
        line_just_entered = (prev_line_for_frame != current_line)
        self.frame_lines[frame_key] = current_line

        # Check line breakpoints (only when line was just entered in this frame)
        if line_just_entered:
            for bp in self.breakpoints.values():
                if bp.enabled and bp.bp_type == "line" and bp.target == current_line:
                    bp.hit_count += 1
                    self.pause(frame, f"Breakpoint #{bp.id} hit at line {current_line}")
                    return

        # Check function entry breakpoints (at frame.ip == 0 on new frame)
        if frame.ip == 0 and frame_key not in self.triggered_fn_frames:
            self.triggered_fn_frames.add(frame_key)
            for bp in self.breakpoints.values():
                if bp.enabled and bp.bp_type == "function" and bp.target == current_fn:
                    bp.hit_count += 1
                    self.pause(frame, f"Breakpoint #{bp.id} hit at {current_fn}()")
                    return

        # Check stepping modes
        if self.step_mode == "stepi":
            self.pause(frame, f"Stepped to instruction at offset {frame.ip:04d}")
            return

        if self.step_mode == "step":
            if frame != self.last_frame or current_line != self.last_line:
                self.pause(frame, f"Stepped to line {current_line}")
                return

        if self.step_mode == "next":
            if current_depth < self.target_depth:
                self.pause(frame, f"Stepped to line {current_line} (returned from function)")
                return
            elif current_depth == self.target_depth and current_line != self.last_line:
                self.pause(frame, f"Stepped to line {current_line}")
                return

        if self.step_mode == "finish":
            if current_depth <= self.target_depth:
                self.pause(frame, f"Finished function, paused at line {current_line}")
                return

    def on_debugger_statement(self, frame: Any) -> None:
        line_idx = max(0, frame.ip - 1)
        current_line = frame.function.chunk.lines[line_idx] if line_idx < len(frame.function.chunk.lines) else 1
        self.pause(frame, f"Hit 'debugger;' statement at line {current_line}")

    def on_ast_debugger(self, node: Any) -> None:
        self.print_line(f"[DEBUG] Hit 'debugger;' statement at line {node.line}")

    def print_status(self, frame: Any, reason: str) -> None:
        current_line = self.get_current_line(frame)
        fn_name = frame.function.name or "<script>"
        self.print_line(f"[DEBUG] {reason}")
        self.print_line(f"  Location: {fn_name}() in {self.filename}:{current_line} (ip: {frame.ip})")
        if self.source_lines and 1 <= current_line <= len(self.source_lines):
            line_text = self.source_lines[current_line - 1]
            self.print_line(f"  -> {current_line:4d} | {line_text}")

    def pause(self, frame: Any, reason: str) -> None:
        self.is_paused = True
        self.print_status(frame, reason)
        self.cmd_loop(frame)
        self.is_paused = False

    def cmd_loop(self, frame: Any) -> None:
        while True:
            try:
                raw_input = self.input_fn("(lang-db) ").strip()
            except (EOFError, KeyboardInterrupt):
                self.print_line("\nExiting debugger...")
                raise DebuggerExit("Execution terminated by user")

            cmd = raw_input if raw_input else self.last_command
            if not cmd:
                continue

            self.last_command = cmd
            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if action in ("c", "continue"):
                self.step_mode = "continue"
                break

            elif action in ("s", "step"):
                self.step_mode = "step"
                self.last_line = self.get_current_line(frame)
                self.last_frame = frame
                break

            elif action in ("n", "next"):
                self.step_mode = "next"
                self.target_depth = len(self.vm.frames)
                self.last_line = self.get_current_line(frame)
                self.last_frame = frame
                break

            elif action in ("si", "stepi"):
                self.step_mode = "stepi"
                break

            elif action in ("fin", "finish", "out"):
                self.step_mode = "finish"
                self.target_depth = len(self.vm.frames) - 1
                break

            elif action in ("b", "break"):
                self.handle_breakpoint_cmd(arg)

            elif action in ("d", "delete"):
                self.handle_delete_cmd(arg)

            elif action in ("info", "breakpoints"):
                if not arg or arg in ("b", "break", "breakpoints"):
                    self.show_breakpoints()
                elif arg == "locals":
                    self.show_locals(frame)
                elif arg == "globals":
                    self.show_globals()
                else:
                    self.print_line(f"Unknown info topic: '{arg}' (try 'info break', 'info locals', 'info globals')")

            elif action == "stack":
                self.show_stack()

            elif action in ("bt", "backtrace", "frames", "where"):
                self.show_frames()

            elif action == "locals":
                self.show_locals(frame)

            elif action == "globals":
                self.show_globals()

            elif action in ("p", "print"):
                self.handle_print_cmd(frame, arg)

            elif action in ("dis", "disasm"):
                self.show_disasm(frame)

            elif action in ("l", "list"):
                self.show_source_list(frame, arg)

            elif action in ("q", "quit", "exit"):
                self.print_line("Exiting debugger...")
                raise DebuggerExit("Execution terminated by user")

            elif action in ("h", "help", "?"):
                self.show_help()

            else:
                self.print_line(f"Unknown command: '{cmd}'. Type 'help' for available commands.")

    def handle_breakpoint_cmd(self, target: str) -> None:
        if not target:
            self.print_line("Usage: break <line_number> OR break <function_name>")
            return

        if target.isdigit():
            line_num = int(target)
            bp = self.add_line_breakpoint(line_num)
            self.print_line(f"Breakpoint #{bp.id} set at line {line_num}")
        else:
            bp = self.add_function_breakpoint(target)
            self.print_line(f"Breakpoint #{bp.id} set at function {target}()")

    def handle_delete_cmd(self, arg: str) -> None:
        if not arg:
            self.clear_breakpoints()
            self.print_line("All breakpoints cleared.")
            return

        if arg.isdigit():
            bp_id = int(arg)
            if self.remove_breakpoint(bp_id):
                self.print_line(f"Breakpoint #{bp_id} deleted.")
            else:
                self.print_line(f"Breakpoint #{bp_id} not found.")
        else:
            self.print_line(f"Invalid breakpoint ID: '{arg}'")

    def show_breakpoints(self) -> None:
        if not self.breakpoints:
            self.print_line("No active breakpoints.")
            return

        self.print_line(f"Breakpoints ({len(self.breakpoints)}):")
        for bp in self.breakpoints.values():
            self.print_line(f"  {bp}")

    def show_stack(self) -> None:
        if not self.vm.stack:
            self.print_line("Operand stack is empty.")
            return

        self.print_line(f"Operand Stack ({len(self.vm.stack)} values):")
        for idx, val in enumerate(self.vm.stack):
            val_type = self.vm._builtin_type(val)
            self.print_line(f"  [{idx:2d}] {val_type:<8}: {repr(val)}")

    def show_frames(self) -> None:
        frames = self.vm.frames
        self.print_line(f"Call Stack ({len(frames)} frames):")
        for idx, f in enumerate(frames):
            fn_name = f.function.name or "<script>"
            line = self.get_current_line(f)
            marker = " <-- active frame" if idx == len(frames) - 1 else ""
            self.print_line(f"  #{idx:2d} {fn_name}() at line {line} (ip: {f.ip}, base slot: {f.slots}){marker}")

    def show_locals(self, frame: Any) -> None:
        frame_idx = self.vm.frames.index(frame) if frame in self.vm.frames else len(self.vm.frames) - 1
        start_slot = frame.slots
        end_slot = len(self.vm.stack)
        if frame_idx + 1 < len(self.vm.frames):
            end_slot = self.vm.frames[frame_idx + 1].slots

        num_slots = end_slot - start_slot
        if num_slots <= 0:
            self.print_line("No local variables in current frame.")
            return

        self.print_line(f"Locals in frame '{frame.function.name or '<script>'}' ({num_slots} slots):")
        for offset in range(num_slots):
            slot_idx = start_slot + offset
            val = self.vm.stack[slot_idx]
            name = frame.function.debug_locals.get(offset, "")
            label = name if name else (f"slot_{offset}" if offset > 0 else ("this" if frame.function.klass else "<callee>"))
            val_type = self.vm._builtin_type(val)
            self.print_line(f"  [{offset:2d}] {label:<12} ({val_type}): {repr(val)}")

    def show_globals(self) -> None:
        user_globals = {
            k: v for k, v in self.vm.globals.items()
            if not callable(v) and not k.startswith("__")
        }
        if not user_globals:
            self.print_line("No user globals defined.")
            return

        self.print_line(f"Global Variables ({len(user_globals)}):")
        for k in sorted(user_globals.keys()):
            v = user_globals[k]
            v_type = self.vm._builtin_type(v)
            self.print_line(f"  {k:<16} ({v_type}): {repr(v)}")

    def handle_print_cmd(self, frame: Any, expr: str) -> None:
        if not expr:
            self.print_line("Usage: print <variable_name> (e.g., 'print x', 'print user.name')")
            return

        val, found = self.resolve_identifier(frame, expr)
        if found:
            val_type = self.vm._builtin_type(val)
            self.print_line(f"{expr} = ({val_type}) {repr(val)}")
        else:
            self.print_line(f"Error: Symbol '{expr}' not found in current scope.")

    def resolve_identifier(self, frame: Any, expr: str) -> Tuple[Any, bool]:
        parts = expr.split(".")
        root_name = parts[0]

        # 1. Search locals in current frame
        found = False
        val = None

        if root_name == "this" and frame.slots < len(self.vm.stack):
            val = self.vm.stack[frame.slots]
            found = True
        else:
            for offset, name in frame.function.debug_locals.items():
                if name == root_name:
                    slot_idx = frame.slots + offset
                    if slot_idx < len(self.vm.stack):
                        val = self.vm.stack[slot_idx]
                        found = True
                        break

        # 2. Search globals
        if not found and root_name in self.vm.globals:
            val = self.vm.globals[root_name]
            found = True

        # 3. Search built-ins
        if not found and root_name in self.vm.builtins:
            val = self.vm.builtins[root_name]
            found = True

        if not found:
            return None, False

        # Property traversal
        for prop in parts[1:]:
            if isinstance(val, InstanceObject) and prop in val.fields:
                val = val.fields[prop]
            elif isinstance(val, InstanceObject) and val.klass and prop in val.klass.methods:
                val = val.klass.methods[prop]
            elif isinstance(val, ClassObject) and prop in val.methods:
                val = val.methods[prop]
            elif isinstance(val, dict) and prop in val:
                val = val[prop]
            else:
                return None, False

        return val, True

    def show_disasm(self, frame: Any) -> None:
        chunk = frame.function.chunk
        fn_name = frame.function.name or "<script>"
        self.print_line(f"Bytecode for {fn_name}() ({len(chunk.code)} bytes):")

        offset = 0
        while offset < len(chunk.code):
            inst_str, next_offset, _ = disassemble_instruction(chunk, offset)
            pointer = "-->" if offset == frame.ip else "   "
            self.print_line(f"  {pointer} {inst_str}")
            offset = next_offset

    def show_source_list(self, frame: Any, arg: str) -> None:
        if not self.source_lines:
            self.print_line("No source code available.")
            return

        current_line = self.get_current_line(frame)
        center = int(arg) if arg.isdigit() else current_line
        start = max(1, center - 5)
        end = min(len(self.source_lines), center + 5)

        self.print_line(f"Source context ({self.filename} lines {start}-{end}):")
        for i in range(start, end + 1):
            marker = " ->" if i == current_line else "   "
            self.print_line(f"{marker} {i:4d} | {self.source_lines[i - 1]}")

    def show_help(self) -> None:
        self.print_line("Simple Compiler Step-Debugger Commands:")
        self.print_line("  step, s              - Step to next source line (step into functions)")
        self.print_line("  next, n              - Step to next source line in current frame (step over)")
        self.print_line("  stepi, si            - Step a single bytecode instruction")
        self.print_line("  finish, fin          - Run until current function returns (step out)")
        self.print_line("  continue, c          - Resume execution until next breakpoint or exit")
        self.print_line("  break, b <target>    - Set breakpoint at line (e.g. 'b 12') or function (e.g. 'b run')")
        self.print_line("  delete, d [id]       - Delete breakpoint by ID, or delete all if omitted")
        self.print_line("  breakpoints, info b  - List all active breakpoints")
        self.print_line("  stack                - Inspect operand stack")
        self.print_line("  frames, bt, where    - Show call stack frames")
        self.print_line("  locals               - Show local variables in the current frame")
        self.print_line("  globals              - Show defined global variables")
        self.print_line("  print, p <name>      - Inspect variable value (e.g. 'p count', 'p obj.prop')")
        self.print_line("  disasm, dis          - Disassemble bytecode with current instruction marker")
        self.print_line("  list, l [line]       - Show surrounding source code")
        self.print_line("  quit, q, exit        - Stop debugging and abort program execution")
        self.print_line("  help, h, ?           - Show this help message")
