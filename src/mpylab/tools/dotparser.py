from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    pos: int


class DotSyntaxError(ValueError):
    def __init__(self, message: str, pos: int | None = None):
        if pos is None:
            super().__init__(message)
        else:
            super().__init__(f"{message} at position {pos}")
        self.pos = pos


class DotTokenizer:
    """
    Tokenizer for the supported DOT subset.
    """

    _TOKEN_RE = re.compile(
        r"""
        (?P<WS>\s+)
      | (?P<HASHCOMMENT>\#.*)
      | (?P<SLASHCOMMENT>//.*)
      | (?P<ARROW>--|->)
      | (?P<LBRACE>\{)
      | (?P<RBRACE>\})
      | (?P<LBRACKET>\[)
      | (?P<RBRACKET>\])
      | (?P<LPAREN>\()
      | (?P<RPAREN>\))
      | (?P<COMMA>,)
      | (?P<COLON>:)
      | (?P<AT>@)
      | (?P<EQUAL>=)
      | (?P<SEMI>;)
      | (?P<STRICT>strict|STRICT)
      | (?P<GRAPH>graph|GRAPH)
      | (?P<DIGRAPH>digraph|DIGRAPH)
      | (?P<NODEKW>node|NODE)
      | (?P<EDGEKW>edge|EDGE)
      | (?P<NUM>[0-9]+)
      | (?P<ID>[_a-zA-Z][_a-zA-Z0-9]*)
      | (?P<STR>"([^\\"]|\\.)*")
        """,
        re.VERBOSE,
    )

    def __init__(self, text: str):
        self.text = text
        self.tokens = list(self._scan(text))
        self.index = 0

    def _scan(self, text: str) -> Iterator[Token]:
        pos = 0
        n = len(text)

        while pos < n:
            m = self._TOKEN_RE.match(text, pos)
            if not m:
                raise DotSyntaxError("Unexpected character", pos)

            kind = m.lastgroup
            value = m.group(kind)
            start = pos
            pos = m.end()

            if kind in {"WS", "HASHCOMMENT", "SLASHCOMMENT"}:
                continue

            yield Token(kind, value, start)

        yield Token("END", "", pos)

    def peek(self) -> Token:
        return self.tokens[self.index]

    def peek_type(self) -> str:
        return self.peek().type

    def accept(self, token_type: str) -> Token | None:
        if self.peek_type() == token_type:
            tok = self.peek()
            self.index += 1
            return tok
        return None

    def expect(self, token_type: str) -> Token:
        tok = self.accept(token_type)
        if tok is None:
            raise DotSyntaxError(
                f"Expected {token_type}, got {self.peek_type()}",
                self.peek().pos,
            )
        return tok


class DotParser:
    """
    Recursive descent parser for the supported DOT subset.

    Result format:
        (nodes, graph)

    nodes:
        {
            node_name: {attr_key: attr_value, ...},
            ...
        }

    graph:
        {
            left_node: {
                right_node: {attr_key: attr_value, ...},
                ...
            },
            ...
        }
    """

    def __init__(self, text: str):
        self.tok = DotTokenizer(text)
        self.nodes: dict[str | int, dict] = {}
        self.graph: dict[str | int, dict] = {}

    def parse(self) -> tuple[dict, dict]:
        self._graph()
        self.tok.expect("END")
        return self.nodes, self.graph

    def _init_nodes_graph(self) -> None:
        self.nodes.clear()
        self.graph.clear()

    def _add_node(self, i, dr=None) -> None:
        if dr is None:
            dr = {}

        if i not in self.nodes:
            self.nodes[i] = dr.copy()
        else:
            self.nodes[i].update(dr)

    def _add_edge(self, left, right=None, attr=None) -> None:
        if right is None:
            right = []
        if attr is None:
            attr = {}

        self._add_node(left)
        for r in right:
            self._add_node(r)

        if left not in self.graph:
            self.graph[left] = {}

        for r in right:
            self.graph[left][r] = attr.copy()

    def _graph(self) -> None:
        self.tok.accept("STRICT")

        if self.tok.accept("GRAPH"):
            self._accept_optional_id()
            self.tok.expect("LBRACE")
            self._init_nodes_graph()
            self._stmt_list()
            self.tok.expect("RBRACE")
            return

        if self.tok.accept("DIGRAPH"):
            self._accept_optional_id()
            self.tok.expect("LBRACE")
            self._init_nodes_graph()
            self._stmt_list()
            self.tok.expect("RBRACE")
            return

        raise DotSyntaxError("Expected graph or digraph", self.tok.peek().pos)

    def _accept_optional_id(self):
        if self.tok.peek_type() in {"ID", "STR", "NUM"}:
            return self._id()
        return None

    def _stmt_list(self) -> None:
        while self.tok.peek_type() != "RBRACE":
            self._stmt()
            self.tok.accept("SEMI")

    def _stmt(self) -> None:
        t = self.tok.peek_type()

        if t in {"GRAPH", "NODEKW", "EDGEKW"}:
            self._attr_stmt()
            return

        if t in {"ID", "STR", "NUM"}:
            i = self._id()

            if self.tok.accept("EQUAL"):
                _ = self._id()
                return

            if self.tok.peek_type() in {"COLON", "AT"}:
                self._port()
                if self.tok.peek_type() == "ARROW":
                    edge_rhs = self._edge_rhs()
                    attrs = {}
                    if self.tok.peek_type() == "LBRACKET":
                        attrs = self._attr_list(None)
                    self._add_edge(i, edge_rhs, attrs)
                else:
                    self._add_node(i)
                return

            if self.tok.peek_type() == "ARROW":
                edge_rhs = self._edge_rhs()
                attrs = {}
                if self.tok.peek_type() == "LBRACKET":
                    attrs = self._attr_list(None)
                self._add_edge(i, edge_rhs, attrs)
                return

            if self.tok.peek_type() == "LBRACKET":
                attrs = self._attr_list(None)
                self._add_node(i, attrs)
                return

            self._add_node(i)
            return

        if t == "LBRACE":
            self.tok.expect("LBRACE")
            self._stmt_list()
            self.tok.expect("RBRACE")
            return

        raise DotSyntaxError("Invalid statement", self.tok.peek().pos)

    def _attr_stmt(self):
        if self.tok.accept("GRAPH"):
            pass
        elif self.tok.accept("NODEKW"):
            pass
        elif self.tok.accept("EDGEKW"):
            pass
        else:
            raise DotSyntaxError("Expected graph/node/edge attribute statement", self.tok.peek().pos)

        return self._attr_list(None)

    def _attr_list(self, adir):
        while self.tok.accept("LBRACKET"):
            if adir is None:
                adir = {}

            if self.tok.peek_type() != "RBRACKET":
                self._a_list(adir)

            self.tok.expect("RBRACKET")

        return adir

    def _a_list(self, adir):
        while self.tok.peek_type() in {"ID", "STR", "NUM"}:
            k = self._id()
            if self.tok.accept("EQUAL"):
                adir[k] = self._id()
            self.tok.accept("COMMA")
        return adir

    def _edge_rhs(self):
        result = []
        while self.tok.accept("ARROW"):
            node_id = self._node_id()
            result.append(node_id)
        return result

    def _node_id(self):
        value = self._id()
        if self.tok.peek_type() in {"COLON", "AT"}:
            self._port()
        return value

    def _port(self):
        if self.tok.peek_type() == "COLON":
            self._port_location()
            if self.tok.peek_type() == "AT":
                self._port_angle()
            return

        if self.tok.peek_type() == "AT":
            self._port_angle()
            if self.tok.peek_type() == "COLON":
                self._port_location()
            return

        raise DotSyntaxError("Expected port", self.tok.peek().pos)

    def _port_location(self):
        self.tok.expect("COLON")
        if self.tok.peek_type() == "LPAREN":
            self.tok.expect("LPAREN")
            self._id()
            self.tok.expect("COMMA")
            self._id()
            self.tok.expect("RPAREN")
        else:
            self._id()

    def _port_angle(self):
        self.tok.expect("AT")
        self._id()

    def _id(self):
        t = self.tok.peek_type()

        if t == "ID":
            return self.tok.expect("ID").value

        if t == "STR":
            return ast.literal_eval(self.tok.expect("STR").value)

        if t == "NUM":
            return int(self.tok.expect("NUM").value)

        raise DotSyntaxError("Expected ID, STR, or NUM", self.tok.peek().pos)


def parse_dot(text: str) -> tuple[dict, dict]:
    return DotParser(text).parse()


def parse(rule: str, text: str):
    """
    Compatibility wrapper for old parse(rule, text) usage.

    Currently only 'graph' is supported.
    """
    if rule != "graph":
        raise NotImplementedError(f"Only rule='graph' is supported, got {rule!r}")
    return parse_dot(text)

def test_typical_graph():
    text = r'''
digraph {
    sg [ini="sg_rs_smb100a.ini"]
    amp1 [ini="amp_ametek_cba_1g_030d.ini" condition="1e6<=f<=1e9"]
    amp2 [ini="amp_ar_25s1g4.ini" condition="800e6<=f<=4.2e9"]
    sw [ini="sw_gtem.ini"]
    prb [ini="prb_lumi_ci250p.ini" condition="30e6<=f<=8.2e9"]

    cbl_sg_amp1 [ini="sg-amp1in.ini" condition="0<=f<=18e9"]
    cbl_amp1_gtem [ini="amp1out-gtem.ini" condition="10e3<=f<=1e9"]

    cbl_sg_amp2 [ini="sg-amp2in.ini" condition="0<=f<=18e9"]
    cbl_amp2_gtem [ini="amp2out-gtem.ini" condition="700e6<=f<=4.2e9"]

    sg -> sg1 [condition="0<=f<=1e9"]
    sg -> sg2 [condition="1e9<f<=18e9"]

    sg1 -> a1i       [dev=cbl_sg_amp1 what="S21"]
    sg2 -> a2i       [dev=cbl_sg_amp2 what="S21"]
    a1i -> amp_in    [condition="0<=f<=1e9"]
    a2i -> amp_in    [condition="1e9<f<=18e9"]

    amp_in -> a1ii   [condition="0<=f<=1e9"]
    amp_in -> a2ii   [condition="1e9<f<=18e9"]

    a1ii -> a1oo     [dev=amp1 what="S21"]
    a2ii -> a2oo     [dev=amp2 what="S21"]

    a1oo -> amp_out  [condition="0<=f<=1e9"]
    a2oo -> amp_out  [condition="1e9<f<=18e9"]

    amp_out -> gtem1 [dev=cbl_amp1_gtem what="S21"]
    amp_out -> gtem2 [dev=cbl_amp2_gtem what="S21"]
    gtem1 -> gtem    [condition="0<=f<=1e9"]
    gtem2 -> gtem    [condition="1e9<f<=18e9"]

    gtem -> prb [condition="0<=f"]
}
'''
    nodes, graph = parse_dot(text)

    print("nodes:", sorted(nodes))
    print("graph sources:", sorted(graph))

    assert "sg" in nodes
    assert "amp1" in nodes
    assert "amp2" in nodes
    assert "prb" in nodes
    assert "sg1" in nodes
    assert "amp_in" in nodes
    assert "gtem" in nodes

    assert nodes["sg"]["ini"] == "sg_rs_smb100a.ini"
    assert nodes["amp1"]["condition"] == "1e6<=f<=1e9"
    assert nodes["prb"]["ini"] == "prb_lumi_ci250p.ini"

    assert graph["sg"]["sg1"]["condition"] == "0<=f<=1e9"
    assert graph["sg"]["sg2"]["condition"] == "1e9<f<=18e9"

    assert graph["sg1"]["a1i"]["dev"] == "cbl_sg_amp1"
    assert graph["sg1"]["a1i"]["what"] == "S21"

    assert graph["a1ii"]["a1oo"]["dev"] == "amp1"
    assert graph["a2ii"]["a2oo"]["dev"] == "amp2"

    assert graph["amp_out"]["gtem1"]["dev"] == "cbl_amp1_gtem"
    assert graph["amp_out"]["gtem2"]["what"] == "S21"

    assert graph["gtem"]["prb"]["condition"] == "0<=f"

    print("test_typical_graph passed")

if __name__ == "__main__":
    test_typical_graph()