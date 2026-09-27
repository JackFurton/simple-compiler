from enum import IntEnum, auto


class OpCode(IntEnum):
    # Literals and constants
    OP_CONSTANT = auto()       # [const_idx: 2 bytes] -> pushes constants[idx]
    OP_NIL = auto()            # pushes nil / None
    OP_TRUE = auto()           # pushes True
    OP_FALSE = auto()          # pushes False

    # Stack manipulation
    OP_POP = auto()            # pops top of stack
    OP_DUP = auto()            # duplicates top of stack

    # Comparisons
    OP_EQUAL = auto()          # [b, a] -> [a == b]
    OP_GREATER = auto()        # [b, a] -> [a > b]
    OP_LESS = auto()           # [b, a] -> [a < b]

    # Arithmetic
    OP_ADD = auto()            # [b, a] -> [a + b]
    OP_SUB = auto()            # [b, a] -> [a - b]
    OP_MUL = auto()            # [b, a] -> [a * b]
    OP_DIV = auto()            # [b, a] -> [a / b]
    OP_MOD = auto()            # [b, a] -> [a % b]

    # Unary
    OP_NOT = auto()            # [a] -> [not a]
    OP_NEGATE = auto()         # [a] -> [-a]

    # Variables
    OP_DEFINE_GLOBAL = auto()  # [name_idx: 2 bytes] pops val, defines globals[name] = val
    OP_GET_GLOBAL = auto()     # [name_idx: 2 bytes] pushes globals[name]
    OP_SET_GLOBAL = auto()     # [name_idx: 2 bytes] assigns globals[name] = peek(0)
    OP_GET_LOCAL = auto()      # [slot: 2 bytes] pushes stack[frame_base + slot]
    OP_SET_LOCAL = auto()      # [slot: 2 bytes] stack[frame_base + slot] = peek(0)

    # Control flow
    OP_JUMP = auto()           # [offset: 2 bytes] ip += offset
    OP_JUMP_IF_FALSE = auto()  # [offset: 2 bytes] if peek(0) is falsy, ip += offset
    OP_LOOP = auto()           # [offset: 2 bytes] ip -= offset

    # Functions, Closures & Calls
    OP_CLOSURE = auto()        # [const_idx: 2 bytes, followed by pairs of (is_local, index)]
    OP_GET_UPVALUE = auto()    # [upvalue_idx: 2 bytes]
    OP_SET_UPVALUE = auto()    # [upvalue_idx: 2 bytes]
    OP_CLOSE_UPVALUE = auto()  # closes upvalue at top of stack and pops it
    OP_CALL = auto()           # [arg_count: 1 byte]
    OP_RETURN = auto()         # returns from current function

    # Collections
    OP_BUILD_LIST = auto()     # [count: 2 bytes] pops count values, pushes list
    OP_BUILD_MAP = auto()      # [count: 2 bytes] pops count pairs, pushes dict
    OP_GET_INDEX = auto()      # [index, target] -> target[index]
    OP_SET_INDEX = auto()      # [val, index, target] -> target[index] = val

    # Output
    OP_PRINT = auto()          # pops val, outputs it
