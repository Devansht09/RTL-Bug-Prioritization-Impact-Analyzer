"""
Dependency Graph + BFS Impact Analysis — Stage 3 & 4
=======================================================
Builds a directed NetworkX graph from RTL assignments.
  Nodes = signals
  Edges = data-flow (RHS_signal → LHS_signal)

BFS traversal from each bug's signal to compute:
  - reach_output   : does propagation ever hit an output port?
  - propagation_depth : shortest path length to nearest output
  - fanout_count   : total number of reachable nodes
  - signal_path    : shortest path list to nearest output
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple

import networkx as nx

from backend.parser.rtl_parser import RTLRepresentation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph Impact Result
# ---------------------------------------------------------------------------

@dataclass
class GraphImpact:
    signal: str
    reach_output: bool
    propagation_depth: int          # 0 if signal IS output; 999 if no path
    fanout_count: int
    signal_path: List[str] = field(default_factory=list)
    affected_outputs: List[str] = field(default_factory=list)
    affected_nodes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

class DependencyGraph:
    """
    Builds and queries the RTL signal dependency graph.
    """

    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()
        self.outputs: Set[str] = set()
        self.inputs: Set[str] = set()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, rep: RTLRepresentation) -> nx.DiGraph:
        """
        Construct graph from RTLRepresentation.
        Edge: src → dst means "dst depends on src" (src drives dst).
        """
        self.graph.clear()
        self.outputs = set(rep.outputs)
        self.inputs = set(rep.inputs)

        # Add ALL declared signals as nodes
        for sig in rep.signals:
            node_attrs = {
                "kind": sig.kind,
                "width": sig.width,
                "module": sig.module,
                "is_output": sig.name in rep.outputs,
                "is_input": sig.name in rep.inputs,
            }
            self.graph.add_node(sig.name, **node_attrs)

        # Add edges from assignments: rhs_signal → lhs_signal
        for asn in rep.assignments:
            if not self.graph.has_node(asn.lhs):
                self.graph.add_node(asn.lhs, kind="implicit", module=asn.module)
            for rhs_sig in asn.rhs_signals:
                if not self.graph.has_node(rhs_sig):
                    self.graph.add_node(rhs_sig, kind="implicit", module=asn.module)
                if rhs_sig != asn.lhs:
                    self.graph.add_edge(
                        rhs_sig, asn.lhs,
                        assignment_kind=asn.kind,
                        module=asn.module,
                    )

        logger.info(
            f"Graph built: {self.graph.number_of_nodes()} nodes, "
            f"{self.graph.number_of_edges()} edges"
        )
        return self.graph

    # ------------------------------------------------------------------
    # BFS Impact Analysis
    # ------------------------------------------------------------------

    def bfs_impact(self, start_signal: str) -> GraphImpact:
        """
        Run BFS from start_signal.
        Returns GraphImpact with reachability metrics.
        """
        G = self.graph

        if start_signal not in G:
            return GraphImpact(
                signal=start_signal,
                reach_output=False,
                propagation_depth=999,
                fanout_count=0,
            )

        # BFS
        visited: Set[str] = set()
        queue: deque = deque([(start_signal, 0)])
        visited.add(start_signal)

        # Track path to nearest output using predecessor map
        predecessor: Dict[str, Optional[str]] = {start_signal: None}
        depth_map: Dict[str, int] = {start_signal: 0}

        nearest_output: Optional[str] = None
        nearest_depth: int = 999
        affected_outputs: List[str] = []

        while queue:
            node, depth = queue.popleft()

            # Check if this is an output node
            is_output = (
                G.nodes[node].get("is_output", False)
                or node in self.outputs
            )
            if is_output and node != start_signal:
                affected_outputs.append(node)
                if depth < nearest_depth:
                    nearest_depth = depth
                    nearest_output = node

            # Continue BFS on successors
            for neighbor in G.successors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    predecessor[neighbor] = node
                    depth_map[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))

        # Build path to nearest output
        signal_path: List[str] = []
        if nearest_output:
            # Trace back
            path: List[str] = []
            cur = nearest_output
            while cur is not None:
                path.append(cur)
                cur = predecessor.get(cur)
            signal_path = list(reversed(path))

        reach_output = bool(affected_outputs)
        propagation_depth = nearest_depth if reach_output else 999
        fanout_count = len(visited) - 1  # exclude start signal itself

        return GraphImpact(
            signal=start_signal,
            reach_output=reach_output,
            propagation_depth=propagation_depth,
            fanout_count=fanout_count,
            signal_path=signal_path,
            affected_outputs=affected_outputs,
            affected_nodes=list(visited - {start_signal}),
        )

    def analyze_all(self, signals: List[str]) -> Dict[str, GraphImpact]:
        """Run BFS impact for all given signals."""
        return {sig: self.bfs_impact(sig) for sig in signals}

    # ------------------------------------------------------------------
    # Graph Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        G = self.graph
        return {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "outputs": list(self.outputs),
            "inputs": list(self.inputs),
            "is_dag": nx.is_directed_acyclic_graph(G),
            "weakly_connected_components": nx.number_weakly_connected_components(G),
        }

    def get_graph_data(self) -> Dict:
        """Serialize graph for frontend visualization."""
        G = self.graph
        nodes = []
        for n, attrs in G.nodes(data=True):
            nodes.append({
                "id": n,
                "kind": attrs.get("kind", "wire"),
                "module": attrs.get("module", ""),
                "is_output": attrs.get("is_output", False),
                "is_input": attrs.get("is_input", False),
            })
        edges = []
        for src, dst, attrs in G.edges(data=True):
            edges.append({
                "source": src,
                "target": dst,
                "kind": attrs.get("assignment_kind", "continuous"),
            })
        return {"nodes": nodes, "edges": edges}
