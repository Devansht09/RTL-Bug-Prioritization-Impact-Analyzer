import sys, io, traceback
sys.path.insert(0, '.')

# Redirect stderr noise
_old_stderr = sys.stderr
sys.stderr = io.StringIO()

try:
    import pyverilog.vparser.parser as vparser
    import tempfile, os

    code = "module test(input a, output b); assign b = a; endmodule"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.v', delete=False, encoding='utf-8') as f:
        f.write(code)
        tmp = f.name

    sys.stderr = _old_stderr
    print(f"Temp file created: {tmp}")
    sys.stderr = io.StringIO()

    ast, directives = vparser.parse([tmp])
    sys.stderr = _old_stderr
    print("PyVerilog parse OK")
    print("AST type:", type(ast))
    os.unlink(tmp)

except Exception as e:
    sys.stderr = _old_stderr
    print(f"Error type: {type(e).__name__}")
    print(f"Error: {e}")
    traceback.print_exc()
