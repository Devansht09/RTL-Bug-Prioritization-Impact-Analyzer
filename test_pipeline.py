import sys, io
sys.path.insert(0, '.')

# Capture stderr (PyVerilog LALR noise)
_old_stderr = sys.stderr
sys.stderr = io.StringIO()

from backend.pipeline import run_pipeline

code = open('examples/simple_alu.v', encoding='utf-8').read()
result = run_pipeline(code)

sys.stderr = _old_stderr

print('=== PARSE INFO ===')
print('  Parse method :', result['parse_info']['method'])
print('  Modules      :', result['parse_info']['modules'])
print('  Signals      :', result['parse_info']['signal_count'])
print('  Assignments  :', result['parse_info']['assignment_count'])
print('  Always blocks:', result['parse_info']['always_block_count'])
print()
print('=== SUMMARY ===')
s = result['summary']
print(f"  Total: {s['total']}  High: {s['high']}  Medium: {s['medium']}  Low: {s['low']}")
print()
print('=== ALL ISSUES (ranked) ===')
for r in result['results']:
    p = ' -> '.join(r['signal_path']) if r['signal_path'] else 'no output path'
    print(f"  #{r['rank']:02d} [{r['severity_label']:6}] {r['signal']:<22} "
          f"score={r['final_score']:.3f}  type={r['bug_type']}")
    print(f"       path: {p}")
print()
print('=== GRAPH ===')
gs = result['graph_stats']
print(f"  Nodes: {gs.get('nodes')}  Edges: {gs.get('edges')}  "
      f"DAG: {gs.get('is_dag')}  Components: {gs.get('weakly_connected_components')}")
print()
print('=== TIMING (ms) ===')
for k, v in result['timing_ms'].items():
    print(f"  {k}: {v}ms")
print()
print('✅ Pipeline smoke test PASSED!')
