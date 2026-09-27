#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler


def test_lists():
    out = []
    c = Compiler(out.append)

    source = """
    let arr = [1, 2, 3];
    print arr[0];
    arr[0] = 100;
    print arr[0];
    append(arr, 200);
    print len(arr);
    let p = pop(arr);
    print p;
    """
    c.run(source)
    assert out == [1, 100, 4, 200]


def test_dictionaries():
    out = []
    c = Compiler(out.append)

    source = """
    let d = {
        "x": 10,
        "y": 20
    };
    print d["x"];
    d["x"] = 99;
    print d["x"];
    print len(keys(d));
    """
    c.run(source)
    assert out == [10, 99, 2]


def run_all():
    test_lists()
    test_dictionaries()
    print("All collections tests passed!")


if __name__ == "__main__":
    run_all()
