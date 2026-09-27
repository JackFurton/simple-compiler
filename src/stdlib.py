import math
import os
import random
import time
from typing import Dict, Callable, Any


def get_stdlib_constants() -> Dict[str, Any]:
    return {
        'PI': math.pi,
        'E': math.e,
    }


def get_stdlib_functions() -> Dict[str, Callable]:
    functions: Dict[str, Callable] = {}

    # --- Math Functions ---
    functions['sqrt'] = lambda x: math.sqrt(x)
    functions['abs'] = lambda x: abs(x)
    functions['min'] = lambda a, b, *args: min(a, b, *args)
    functions['max'] = lambda a, b, *args: max(a, b, *args)
    functions['floor'] = lambda x: math.floor(x)
    functions['ceil'] = lambda x: math.ceil(x)
    functions['round'] = lambda x, ndigits=0: round(x, int(ndigits)) if int(ndigits) > 0 else round(x)
    functions['sin'] = lambda x: math.sin(x)
    functions['cos'] = lambda x: math.cos(x)
    functions['tan'] = lambda x: math.tan(x)
    functions['random'] = random.random
    functions['randint'] = lambda a, b: random.randint(int(a), int(b))

    # --- File I/O Functions ---
    def _read_file(path: str) -> str:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _write_file(path: str, content: Any) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(str(content))
        return None

    def _append_file(path: str, content: Any) -> None:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(str(content))
        return None

    def _remove_file(path: str) -> bool:
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    functions['read_file'] = _read_file
    functions['write_file'] = _write_file
    functions['append_file'] = _append_file
    functions['file_exists'] = os.path.exists
    functions['remove_file'] = _remove_file

    # --- String Utilities ---
    functions['split'] = lambda s, sep=None: str(s).split(str(sep) if sep is not None else None)
    functions['join'] = lambda lst, sep="": str(sep).join(str(x) for x in lst)
    functions['replace'] = lambda s, old, new: str(s).replace(str(old), str(new))
    functions['trim'] = lambda s: str(s).strip()
    functions['to_upper'] = lambda s: str(s).upper()
    functions['to_lower'] = lambda s: str(s).lower()
    functions['starts_with'] = lambda s, prefix: str(s).startswith(str(prefix))
    functions['ends_with'] = lambda s, suffix: str(s).endswith(str(suffix))
    functions['char_at'] = lambda s, idx: str(s)[int(idx)]
    functions['substring'] = lambda s, start, end=None: str(s)[int(start): int(end) if end is not None else len(str(s))]

    def _contains(collection: Any, item: Any) -> bool:
        if isinstance(collection, str):
            return str(item) in collection
        if hasattr(collection, '__contains__'):
            return item in collection
        return False

    functions['contains'] = _contains

    # --- System & Environment ---
    functions['sleep'] = lambda seconds: time.sleep(float(seconds))
    functions['env'] = lambda key, default=None: os.environ.get(str(key), default)

    return functions
