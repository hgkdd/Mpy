import ast

nodes = {}
graph = {}


def init_nodes_graph():
    nodes.clear()
    graph.clear()


def add_node(i, dr=None):
    if dr is None:
        dr = {}

    if i not in nodes:
        nodes[i] = dr.copy()
    else:
        nodes[i].update(dr)


def add_edge(left, right=None, attr=None):
    if right is None:
        right = []
    if attr is None:
        attr = {}

    add_node(left)
    for r in right:
        add_node(r)

    if left not in graph:
        graph[left] = {}

    for r in right:
        graph[left][r] = attr.copy()


%%
parser DOT:
    ignore: '\\s+'
    ignore: '#.*'
    ignore: '//.*'

    token NUM:   '[0-9]+'
    token ID:    '[_a-zA-Z][_a-zA-Z0-9]*'
    token STR:   '"([^\\"]+|\\\\.)*"'
    token END:   "$"

    rule graph:  ['strict|STRICT'] (
                      'graph|GRAPH' [id]
                      '{' {{ init_nodes_graph() }}
                      stmt_list
                      '}'
                    | 'digraph|DIGRAPH' [id]
                      '{' {{ init_nodes_graph() }}
                      stmt_list
                      '}'
                    ) END {{ return (nodes, graph) }}

    rule stmt_list:
        (
            stmt
            [';']
        )*

    rule stmt:
          attr_stmt
        | id {{ i = id }}
          (
              '=' id {{ j = id }}
            | port (
                  edgeRHS {{ l = {} }} [attr_list<<None>> {{ l = attr_list }}] {{ add_edge(i, edgeRHS, l) }}
                | {{ add_node(i) }}
              )
            | edgeRHS {{ l = {} }} [attr_list<<None>> {{ l = attr_list }}] {{ add_edge(i, edgeRHS, l) }}
            | attr_list<<None>> {{ add_node(i, attr_list) }}
            | {{ add_node(i) }}
          )
        | '{' stmt_list '}'

    rule attr_stmt:
        (
            'graph|GRAPH'
          | 'node|NODE'
          | 'edge|EDGE'
        )
        attr_list<<None>> {{ return attr_list }}

    rule attr_list <<adir>>:
        (
            '\\[' {{ if adir is None: adir = {} }}
                [a_list<<adir>>]
            '\\]'
        )+ {{ return adir }}

    rule a_list <<adir>>:
        (
            id {{ k = id }}
            ['=' id {{ adir[k] = id }}]
            [',']
        )+ {{ return adir }}

    rule edge_stmt:
        node_id edgeRHS [attr_list<<None>>]

    rule edgeRHS:
        (
            {{ list = [] }}
            '--|->'
            node_id {{ list.append(node_id) }}
        )+ {{ return list }}

    rule node_stmt:
        node_id {{ nodes[node_id] = {} }}
        [attr_list<<None>> {{ nodes[node_id] = attr_list }}]
        {{ return nodes }}

    rule node_id:
        id [port] {{ return id }}

    rule port:
        (
            port_location [port_angle]
          | port_angle [port_location]
        )

    rule port_location:
        ':' (
            id
          | '\\(' id ',' id '\\)'
        )

    rule port_angle:
        '@' id

    rule id:
          ID  {{ return ID }}
        | STR {{ return ast.literal_eval(STR) }}
        | NUM {{ return int(NUM) }}
