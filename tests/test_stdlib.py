#!/usr/bin/env python3

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler


def test_stdlib_math():
    out = []
    c = Compiler(out.append)

    source = """
    print sqrt(16);
    print abs(-42);
    print min(10, 20);
    print max(10, 20);
    print floor(4.9);
    print ceil(4.1);
    print round(3.14159, 2);
    print PI > 3.14 and PI < 3.15;
    print E > 2.71 and E < 2.72;
    """
    c.run(source)
    assert out[0] == 4.0
    assert out[1] == 42
    assert out[2] == 10
    assert out[3] == 20
    assert out[4] == 4
    assert out[5] == 5
    assert out[6] == 3.14
    assert out[7] is True
    assert out[8] is True


def test_stdlib_strings():
    out = []
    c = Compiler(out.append)

    source = """
    let parts = split("apple,banana,orange", ",");
    print len(parts);
    print parts[1];
    print join(parts, " - ");
    print replace("hello world", "world", "simple-compiler");
    print trim("   spaced text   ");
    print to_upper("lowercase");
    print to_lower("UPPERCASE");
    print starts_with("filename.lang", "file");
    print ends_with("filename.lang", ".lang");
    print contains("supercalifragilistic", "cali");
    print char_at("python", 0);
    print substring("compilation", 0, 7);
    """
    c.run(source)
    assert out[0] == 3
    assert out[1] == "banana"
    assert out[2] == "apple - banana - orange"
    assert out[3] == "hello simple-compiler"
    assert out[4] == "spaced text"
    assert out[5] == "LOWERCASE"
    assert out[6] == "uppercase"
    assert out[7] is True
    assert out[8] is True
    assert out[9] is True
    assert out[10] == "p"
    assert out[11] == "compila"


def test_stdlib_file_io():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        out = []
        c = Compiler(out.append)

        source = f"""
        write_file("{tmp_path}", "Line 1\\n");
        append_file("{tmp_path}", "Line 2\\n");
        let content = read_file("{tmp_path}");
        print contains(content, "Line 1");
        print contains(content, "Line 2");
        print file_exists("{tmp_path}");
        remove_file("{tmp_path}");
        print file_exists("{tmp_path}");
        """
        c.run(source)
        assert out == [True, True, True, False]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def run_all():
    test_stdlib_math()
    test_stdlib_strings()
    test_stdlib_file_io()
    print("All stdlib tests passed!")


if __name__ == "__main__":
    run_all()
