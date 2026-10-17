#!/usr/bin/env python3

import sys
import unittest
import tempfile
import subprocess
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler
from interpreter import interpret_string


class TestLambdasAndHigherOrderFunctions(unittest.TestCase):
    def setUp(self):
        self.compiler = Compiler()
        self.has_cc = shutil.which("gcc") is not None or shutil.which("clang") is not None

    def _run_all_backends(self, source: str, test_c: bool = True):
        # 1. Bytecode VM
        vm_out = []
        vm_compiler = Compiler(output_callback=lambda x: vm_out.append(str(x)))
        vm_compiler.run(source)

        # 2. Tree-walk Interpreter
        interp_out = []
        interpret_string(source, output_callback=lambda x: interp_out.append(str(x)))
        self.assertEqual(vm_out, interp_out, "VM and Interpreter outputs differed")

        # 3. Native C Transpiler (when closures are not required by test_c=False)
        if test_c and self.has_cc:
            with tempfile.TemporaryDirectory() as tmpdir:
                src_path = str(Path(tmpdir) / "prog.lang")
                bin_path = str(Path(tmpdir) / "prog")
                Path(src_path).write_text(source, encoding="utf-8")
                self.compiler.build_native(src_path, bin_path)
                proc = subprocess.run([bin_path], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, f"C binary failed: {proc.stderr}")
                c_out = proc.stdout.strip().splitlines() if proc.stdout.strip() else []
                self.assertEqual(vm_out, c_out, "VM and C outputs differed")

        return vm_out

    def test_lambda_expression_assignment(self):
        code = """
        let square = fn(x) { return x * x; };
        let add = fn(a, b) { return a + b; };
        print square(6);
        print add(10, 25);
        print type(square);
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, ["36", "35", "function"])

    def test_immediately_invoked_lambda(self):
        code = """
        let res = (fn(x, y) { return x * y + 1; })(4, 5);
        print res;
        print fn(msg) { return "hello " + msg; }("world");
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, ["21", "hello world"])

    def test_lambda_closure_capture(self):
        code = """
        fn make_adder(base) {
            return fn(x) {
                return base + x;
            };
        }
        let add5 = make_adder(5);
        let add10 = make_adder(10);
        print add5(3);
        print add10(3);
        """
        out = self._run_all_backends(code, test_c=False)
        self.assertEqual(out, ["8", "13"])

    def test_map_builtin(self):
        code = """
        let nums = [1, 2, 3, 4];
        let doubled = map(fn(x) { return x * 2; }, nums);
        print doubled;

        fn triple(n) { return n * 3; }
        print map(triple, nums);
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, ["[2, 4, 6, 8]", "[3, 6, 9, 12]"])

    def test_filter_builtin(self):
        code = """
        let nums = [1, 2, 3, 4, 5, 6];
        let evens = filter(fn(x) { return x % 2 == 0; }, nums);
        print evens;
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, ["[2, 4, 6]"])

    def test_reduce_builtin(self):
        code = """
        let nums = [1, 2, 3, 4, 5];
        let sum1 = reduce(fn(acc, x) { return acc + x; }, nums);
        let sum2 = reduce(fn(acc, x) { return acc + x; }, nums, 100);
        print sum1;
        print sum2;
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, ["15", "115"])

    def test_chained_higher_order_pipeline(self):
        code = """
        let data = [1, 2, 3, 4, 5, 6];
        let result = reduce(
            fn(a, b) { return a + b; },
            map(
                fn(x) { return x * x; },
                filter(fn(x) { return x % 2 == 1; }, data)
            ),
            0
        );
        print result;
        """
        out = self._run_all_backends(code)
        # Odd numbers: 1, 3, 5 -> squares: 1, 9, 25 -> sum: 35
        self.assertEqual(out, ["35"])

    def test_exception_inside_higher_order_callback(self):
        code = """
        try {
            map(fn(x) {
                if (x == 3) {
                    throw "hit three";
                }
                return x;
            }, [1, 2, 3, 4]);
            print "unreachable";
        } catch (e) {
            print "caught: " + e;
        }
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, ["caught: hit three"])


if __name__ == "__main__":
    unittest.main()
