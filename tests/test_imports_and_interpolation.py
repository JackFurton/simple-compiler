#!/usr/bin/env python3

import sys
import unittest
import tempfile
import subprocess
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler, CompilerError
from interpreter import interpret_string
from tokens import TokenType


class TestImportsAndInterpolation(unittest.TestCase):
    def setUp(self):
        self.compiler = Compiler()
        self.has_cc = shutil.which("gcc") is not None or shutil.which("clang") is not None

    def _run_all_backends(self, source: str, base_dir: str = None, test_c: bool = True):
        # 1. Bytecode VM
        vm_out = []
        vm_compiler = Compiler(output_callback=lambda x: vm_out.append(str(x)))
        vm_compiler.run(source, base_dir=base_dir)

        # 2. Tree-walk Interpreter
        interp_out = []
        interpret_string(source, output_callback=lambda x: interp_out.append(str(x)), base_dir=base_dir)
        self.assertEqual(vm_out, interp_out, "VM and Interpreter outputs differed")

        # 3. Native C Transpiler
        if test_c and self.has_cc:
            with tempfile.TemporaryDirectory() as tmpdir:
                work_dir = Path(base_dir) if base_dir else Path(tmpdir)
                src_path = str(work_dir / "_entry_prog.lang")
                bin_path = str(Path(tmpdir) / "prog")
                try:
                    Path(src_path).write_text(source, encoding="utf-8")
                    self.compiler.build_native(src_path, bin_path)
                    proc = subprocess.run([bin_path], capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, f"C binary failed: {proc.stderr}")
                    c_out = proc.stdout.strip().splitlines() if proc.stdout.strip() else []
                    self.assertEqual(vm_out, c_out, "VM and C outputs differed")
                finally:
                    Path(src_path).unlink(missing_ok=True)
                    Path(src_path).with_suffix(".c").unlink(missing_ok=True)

        return vm_out

    def test_import_token(self):
        tokens = self.compiler.tokenize('import "math_utils.lang";')
        types = [t.type for t in tokens]
        self.assertIn(TokenType.IMPORT, types)

    def test_string_interpolation_basic(self):
        code = """
        let name = "Ada";
        let age = 36;
        print "Hello ${name}, age ${age}!";
        print "${name} in 4 years: ${age + 4}";
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, ["Hello Ada, age 36!", "Ada in 4 years: 40"])

    def test_string_interpolation_expressions_and_escaped_dollar(self):
        code = """
        fn double(x) { return x * 2; }
        let items = [10, 20, 30];
        print "first=${items[0]}, doubled=${double(items[1])}";
        print "literal \\${not_interpolated} and ${1 + 2}";
        """
        out = self._run_all_backends(code)
        self.assertEqual(out, [
            "first=10, doubled=40",
            "literal ${not_interpolated} and 3"
        ])

    def test_module_import_functions_and_classes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mod_path = Path(tmpdir) / "math_mod.lang"
            mod_path.write_text("""
            let SCALE = 10;
            fn scale_val(x) {
                return x * SCALE;
            }
            class Box {
                init(v) {
                    this.v = v;
                }
                describe() {
                    return "Box(${this.v})";
                }
            }
            """, encoding="utf-8")

            main_code = """
            import "math_mod.lang";
            print scale_val(7);
            let b = Box(42);
            print b.describe();
            """
            out = self._run_all_backends(main_code, base_dir=tmpdir)
            self.assertEqual(out, ["70", "Box(42)"])

    def test_nested_and_deduplicated_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub_dir = Path(tmpdir) / "sub"
            sub_dir.mkdir()

            leaf_path = sub_dir / "leaf.lang"
            leaf_path.write_text("""
            print "leaf_loaded";
            fn leaf_fn() { return "from_leaf"; }
            """, encoding="utf-8")

            mid_path = sub_dir / "mid.lang"
            mid_path.write_text("""
            import "leaf.lang";
            fn mid_fn() { return leaf_fn() + "+mid"; }
            """, encoding="utf-8")

            main_code = """
            import "sub/mid.lang";
            import "sub/leaf.lang";
            print mid_fn();
            """
            out = self._run_all_backends(main_code, base_dir=tmpdir)
            # leaf_loaded must only execute once despite being imported by both mid.lang and main
            self.assertEqual(out, ["leaf_loaded", "from_leaf+mid"])

    def test_missing_module_raises_error(self):
        with self.assertRaises(CompilerError):
            self.compiler.run('import "non_existent_module_xyz.lang";')


if __name__ == "__main__":
    unittest.main()
