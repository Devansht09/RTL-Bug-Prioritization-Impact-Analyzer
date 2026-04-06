"""
RTL Parser — Stage 1 of the Pipeline
======================================
Attempts PyVerilog AST parsing first. Falls back to a robust regex-based
parser if PyVerilog is unavailable or fails. Both paths produce the same
RTLRepresentation output format.
"""

from __future__ import annotations

import re
import os
import sys
import tempfile
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    name: str
    kind: str          # 'input', 'output', 'wire', 'reg', 'inout'
    width: str         # e.g. "[7:0]" or ""
    module: str


@dataclass
class Assignment:
    lhs: str           # left-hand side signal name
    rhs_signals: List[str]   # signals found on right-hand side
    kind: str          # 'continuous' | 'procedural'
    module: str
    line: int = 0


@dataclass
class AlwaysBlock:
    sensitivity: str   # raw sensitivity list string
    assignments: List[Assignment] = field(default_factory=list)
    module: str = ""
    line: int = 0
    has_default: bool = False   # True if default/else covers all paths


@dataclass
class RTLRepresentation:
    signals: List[Signal] = field(default_factory=list)
    assignments: List[Assignment] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    always_blocks: List[AlwaysBlock] = field(default_factory=list)
    outputs: Set[str] = field(default_factory=set)
    inputs: Set[str] = field(default_factory=set)
    parse_method: str = "unknown"   # 'pyverilog' | 'regex'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIGNAL_RE = re.compile(
    r'\b(input|output|inout|wire|reg)\s*'
    r'(?:wire\s+|reg\s+)?'
    r'(\[\s*\d+\s*:\s*\d+\s*\])?\s*'
    r'(\w+)\s*[;,]',
    re.MULTILINE,
)

_MODULE_RE = re.compile(r'\bmodule\s+(\w+)\s*[#(]', re.MULTILINE)

_ASSIGN_RE = re.compile(
    r'\bassign\s+(\w+)\s*=\s*([^;]+);', re.MULTILINE
)

_ALWAYS_RE = re.compile(
    r'\balways\s*@\s*\(([^)]*)\)\s*begin(.*?)end\b',
    re.DOTALL,
)

_PROC_ASSIGN_RE = re.compile(
    r'(\w+)\s*(?:<=|=)\s*([^;]+);', re.MULTILINE
)

_IDENT_RE = re.compile(r'\b([a-zA-Z_]\w*)\b')

# Keywords to exclude from signal names
_KEYWORDS = {
    'begin', 'end', 'if', 'else', 'case', 'endcase', 'default',
    'always', 'assign', 'module', 'endmodule', 'input', 'output',
    'inout', 'wire', 'reg', 'integer', 'parameter', 'localparam',
    'posedge', 'negedge', 'or', 'and', 'not', 'for', 'while',
}


def _extract_rhs_signals(expr: str) -> List[str]:
    """Pull all likely signal identifiers from an expression."""
    tokens = _IDENT_RE.findall(expr)
    return [t for t in tokens if t not in _KEYWORDS and not t[0].isdigit()]


def _strip_comments(code: str) -> str:
    """Remove // and /* */ comments."""
    code = re.sub(r'//[^\n]*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    return code


# ---------------------------------------------------------------------------
# Regex-Based Parser (fallback)
# ---------------------------------------------------------------------------

class RegexParser:
    """
    Lightweight regex parser. Extracts:
    - Module names
    - Signal declarations (input/output/wire/reg)
    - Continuous assignments
    - Always block assignments + sensitivity lists
    """

    def parse(self, code: str) -> RTLRepresentation:
        code_clean = _strip_comments(code)
        rep = RTLRepresentation(parse_method='regex')

        # --- Modules ---
        modules = _MODULE_RE.findall(code_clean)
        rep.modules = modules
        current_module = modules[0] if modules else "unknown"

        # --- Split by module for better attribution ---
        module_blocks = self._split_by_module(code_clean, modules)

        for mod_name, mod_code in module_blocks:
            self._parse_module(mod_name, mod_code, rep)

        return rep

    def _split_by_module(
        self, code: str, modules: List[str]
    ) -> List[Tuple[str, str]]:
        """Split code into per-module blocks."""
        if not modules:
            return [("unknown", code)]
        results = []
        pattern = re.compile(r'\bmodule\s+(\w+)', re.MULTILINE)
        positions = [(m.group(1), m.start()) for m in pattern.finditer(code)]
        for i, (mod_name, start) in enumerate(positions):
            end = positions[i + 1][1] if i + 1 < len(positions) else len(code)
            results.append((mod_name, code[start:end]))
        return results

    def _parse_module(self, mod_name: str, code: str, rep: RTLRepresentation):
        # Signals
        for m in _SIGNAL_RE.finditer(code):
            kind = m.group(1)
            width = (m.group(2) or "").strip()
            name = m.group(3)
            if name in _KEYWORDS:
                continue
            sig = Signal(name=name, kind=kind, width=width, module=mod_name)
            rep.signals.append(sig)
            if kind == 'output':
                rep.outputs.add(name)
            elif kind == 'input':
                rep.inputs.add(name)

        # Continuous assignments
        for m in _ASSIGN_RE.finditer(code):
            lhs = m.group(1).strip()
            rhs_raw = m.group(2).strip()
            rhs_sigs = _extract_rhs_signals(rhs_raw)
            line = code[:m.start()].count('\n') + 1
            rep.assignments.append(Assignment(
                lhs=lhs,
                rhs_signals=rhs_sigs,
                kind='continuous',
                module=mod_name,
                line=line,
            ))

        # Always blocks
        for m in _ALWAYS_RE.finditer(code):
            sensitivity = m.group(1).strip()
            body = m.group(2)
            line = code[:m.start()].count('\n') + 1
            block = AlwaysBlock(
                sensitivity=sensitivity,
                module=mod_name,
                line=line,
            )
            # Check for default/else coverage
            block.has_default = bool(
                re.search(r'\bdefault\b|\belse\b', body)
            )
            # Extract procedural assignments
            for am in _PROC_ASSIGN_RE.finditer(body):
                lhs = am.group(1).strip()
                rhs_raw = am.group(2).strip()
                if lhs in _KEYWORDS:
                    continue
                rhs_sigs = _extract_rhs_signals(rhs_raw)
                al = code[:m.start()].count('\n') + 1
                block.assignments.append(Assignment(
                    lhs=lhs,
                    rhs_signals=rhs_sigs,
                    kind='procedural',
                    module=mod_name,
                    line=al,
                ))
                rep.assignments.append(Assignment(
                    lhs=lhs,
                    rhs_signals=rhs_sigs,
                    kind='procedural',
                    module=mod_name,
                    line=al,
                ))
            rep.always_blocks.append(block)


# ---------------------------------------------------------------------------
# PyVerilog-Based Parser (primary)
# ---------------------------------------------------------------------------

class PyVerilogParser:
    """
    Uses PyVerilog AST for accurate parsing.
    If unavailable, raises ImportError — caller should fall back.
    """

    def parse(self, code: str) -> RTLRepresentation:
        try:
            import pyverilog.vparser.parser as vparser
            from pyverilog.vparser.ast import (
                ModuleDef, Decl, Input, Output, Inout, Wire, Reg,
                Assign, Lvalue, Rvalue, Always, SensList, Sens,
                IfStatement, CaseStatement, Case,
            )
        except ImportError:
            raise ImportError("PyVerilog not installed")

        rep = RTLRepresentation(parse_method='pyverilog')

        # Write to temp file (PyVerilog needs file path)
        # Use delete=False + manual cleanup to avoid Windows file-lock issues
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.v', delete=False, encoding='utf-8'
            ) as f:
                f.write(code)
                tmp_path = f.name
            # Avoid Read-Only File System on Vercel Serverless by writing parser tabs to /tmp
            import tempfile
            old_cwd = os.getcwd()
            try:
                os.chdir(tempfile.gettempdir())
                ast, _ = vparser.parse([tmp_path])
            finally:
                os.chdir(old_cwd)
            self._walk(ast, rep)
        except Exception as e:
            logger.warning(f"PyVerilog parse failed: {e}")
            raise
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass  # Windows may still lock it briefly; ignore

        return rep

    def _walk(self, node, rep: RTLRepresentation, module_name: str = ""):
        from pyverilog.vparser.ast import (
            ModuleDef, Decl, Input, Output, Inout, Wire, Reg,
            Assign, Always, SensList,
        )

        if node is None:
            return

        if isinstance(node, ModuleDef):
            module_name = node.name
            if module_name not in rep.modules:
                rep.modules.append(module_name)

        elif isinstance(node, (Input, Output, Inout, Wire, Reg)):
            kind = type(node).__name__.lower()
            name = node.name
            width = ""
            if hasattr(node, 'width') and node.width:
                try:
                    msb = node.width.msb
                    lsb = node.width.lsb
                    width = f"[{msb}:{lsb}]"
                except Exception:
                    pass
            rep.signals.append(Signal(
                name=name, kind=kind, width=width, module=module_name
            ))
            if kind == 'output':
                rep.outputs.add(name)
            elif kind == 'input':
                rep.inputs.add(name)

        elif isinstance(node, Assign):
            lhs_name = self._lvalue_name(node.left)
            rhs_sigs = self._collect_identifiers(node.right)
            if lhs_name:
                rep.assignments.append(Assignment(
                    lhs=lhs_name,
                    rhs_signals=rhs_sigs,
                    kind='continuous',
                    module=module_name,
                    line=node.lineno if hasattr(node, 'lineno') else 0,
                ))

        elif isinstance(node, Always):
            sens_str = str(node.sens_list) if node.sens_list else "*"
            block = AlwaysBlock(
                sensitivity=sens_str,
                module=module_name,
                line=node.lineno if hasattr(node, 'lineno') else 0,
            )
            self._walk_always_body(node.statement, block, rep, module_name)
            rep.always_blocks.append(block)
            return  # children already handled

        # Recurse children
        for child in node.children():
            self._walk(child, rep, module_name)

    def _walk_always_body(self, node, block: AlwaysBlock, rep, module_name):
        from pyverilog.vparser.ast import (
            BlockingSubstitution, NonblockingSubstitution,
            IfStatement, CaseStatement,
        )
        if node is None:
            return

        if isinstance(node, (BlockingSubstitution, NonblockingSubstitution)):
            lhs_name = self._lvalue_name(node.left)
            rhs_sigs = self._collect_identifiers(node.right)
            if lhs_name:
                a = Assignment(
                    lhs=lhs_name, rhs_signals=rhs_sigs,
                    kind='procedural', module=module_name,
                    line=node.lineno if hasattr(node, 'lineno') else 0,
                )
                block.assignments.append(a)
                rep.assignments.append(a)
        elif isinstance(node, IfStatement):
            block.has_default = True  # if/else = coverage
        elif isinstance(node, CaseStatement):
            # Check for default
            if hasattr(node, 'caselist'):
                for c in node.caselist:
                    if c.cond is None:
                        block.has_default = True

        for child in node.children():
            self._walk_always_body(child, block, rep, module_name)

    def _lvalue_name(self, node) -> Optional[str]:
        if node is None:
            return None
        from pyverilog.vparser.ast import Lvalue, Identifier, Partselect, Pointer
        if hasattr(node, 'var'):
            return self._lvalue_name(node.var)
        if hasattr(node, 'name'):
            return node.name
        return None

    def _collect_identifiers(self, node) -> List[str]:
        from pyverilog.vparser.ast import Identifier
        if node is None:
            return []
        results = []
        if isinstance(node, Identifier):
            if node.name not in _KEYWORDS:
                results.append(node.name)
        for child in node.children():
            results.extend(self._collect_identifiers(child))
        return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_rtl(code: str) -> RTLRepresentation:
    """
    Parse RTL code. Tries PyVerilog first, falls back to regex parser.
    Always returns an RTLRepresentation.
    """
    # Try PyVerilog
    pv = PyVerilogParser()
    try:
        rep = pv.parse(code)
        logger.info(
            f"Parsed with PyVerilog: {len(rep.modules)} modules, "
            f"{len(rep.signals)} signals, {len(rep.assignments)} assignments"
        )
        return rep
    except Exception as e:
        logger.warning(f"PyVerilog failed ({e}), using regex fallback.")

    # Fallback to regex
    rx = RegexParser()
    rep = rx.parse(code)
    logger.info(
        f"Parsed with regex: {len(rep.modules)} modules, "
        f"{len(rep.signals)} signals, {len(rep.assignments)} assignments"
    )
    return rep
