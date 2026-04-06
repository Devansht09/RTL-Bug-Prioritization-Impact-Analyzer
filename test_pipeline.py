import sys, io
sys.path.insert(0, '.')
sys.stderr = io.StringIO()

from backend.pipeline import run_pipeline
sys.stderr = io.StringIO()

code = open('examples/simple_alu.v', encoding='utf-8').read()
result = run_pipeline(code)
sys.stderr = sys.__stderr__

lines = []
lines.append("=== PARSE INFO ===")
lines.append(f"  Modules: {result['parse_info']['modules']}")
lines.append(f"  Signals: {result['parse_info']['signal_count']}")
lines.append("")
lines.append("=== SUMMARY ===")
s = result['summary']
lines.append(f"  Total={s['total']}  High={s['high']}  Medium={s['medium']}  Low={s['low']}")
lines.append("")
lines.append("=== ALL ISSUES (ranked) ===")
for r in result['results']:
    path = ' -> '.join(r['signal_path']) if r['signal_path'] else 'no output path'
    lines.append(f"  #{r['rank']:02d} [{r['severity_label']:6}] {r['signal']:<22} score={r['final_score']:.3f}  reach={r['reach_output']}  depth={r['propagation_depth']}  fanout={r['fanout_count']}")
    lines.append(f"         path: {path}")

lines.append("")
lines.append("=== GRAPH ===")
gs = result['graph_stats']
lines.append(f"  Nodes={gs.get('nodes')}  Edges={gs.get('edges')}")
lines.append("")
lines.append("DONE")

with open('test_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Written to test_output.txt")
