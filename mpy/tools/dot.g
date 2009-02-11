nodes = {}
graph = {}

def init_nodes_graph():
    for n in nodes.keys():
        del(nodes[str(n)])
    for n in graph.keys():
        del(graph[str(n)])

def add_node(i, dir={}):
    if i not in nodes.keys():
        nodes[i] = dir.copy()         # new node
    else:                             # node already exist
        for (k,v) in dir.items(): 
             nodes[i][k]=v
            
def add_edge(left, right=[], attr={}):
    # add nodes
    add_node (left)
    for r in right:
        add_node (r)
    if left not in graph.keys():   # new left side (source)
        right_dict ={}
        for r in right:
            right_dict[r]=attr.copy()
    else:
        right_dict = graph[left].copy()
        for r in right:
            right_dict[r]=attr.copy()
    graph[left]=right_dict.copy()
        

%%
parser DOT:
    ignore: '\\s+'
    ignore: '#.*'
    ignore: '//.*'

    token NUM:   '[0-9]+'
    token ID:    '[_a-zA-Z][_a-zA-Z0-9]*' 
    token STR:   '"([^\\"]+|\\\\.)*"'
    token END:   "$"

    rule graph:  ['strict|STRICT'] ( 'graph|GRAPH' [id]
                                   '{'  {{ init_nodes_graph() }}         # match opening {
                                   ( stmt_list  
                                     )
                                   '}' 
                                 | 'digraph|DIGRAPH' [id]
                                   '{'  {{ init_nodes_graph() }}         # match opening {
                                   ( stmt_list
                                     )
                                   '}'
                                   ) END  {{ return (nodes, graph) }}

    rule stmt_list:  (
                        stmt     # a stmt, opt. ','
                        [';']
                     )*

    rule stmt: (  attr_stmt                            # attrib_stmt
                 | id  {{ i = id }}
                   (
                     '=' id   {{ j = id }}  # id_stmt
                     | port
                       (
                         edgeRHS {{ l = {} }} [attr_list<<None>> {{ l=attr_list }} ]  {{ add_edge(i,edgeRHS,l) }}            # egde_stmt
                        |  {{ add_node(i) }}      # node_stmt
                       )
                     | edgeRHS {{ l = {} }} [attr_list<<None>> {{ l=attr_list }} ]  {{ add_edge(i,edgeRHS,l) }}   # egde_stmt
                     | attr_list<<None>>  {{ add_node (i, attr_list ) }}  # node with attribs
                     |     {{ add_node(i) }} # node_stmt without attribs
                    )
                  | 'subgraph|SUBGRAPH'
                    (
                        edgeRHS {{ l = {} }} [attr_list<<None>> {{ l=attr_list }} ]  {{ add_edge(i,edgeRHS,l) }}        # egde_stmt
                     | '{' stmt_list '}'         # subgraph_stmt
                     | id
                       (
                         '{' stmt_list '}'         # subgraph_stmt
                        |                              # subgraph_stmt
                       )
                    )
                   | '{' stmt_list '}'                  # subgraph_stmt
                 )

                 
    rule attr_stmt: (   'graph|GRAPH'
                      | 'node|NODE'
                      | 'edge|EDGE'
                    ) attr_list<<None>>  {{ return attr_list }}

    rule attr_list <<adir>>: (                   
                '\\[' {{ if adir is None: adir={} }}                  
                    [ a_list<<adir>> ]   {{  }}
                '\\]'                  
               )+                      {{ return adir }}

    rule a_list <<adir>>: ( 
                              id            {{ k = id }}
                              [ '=' id {{ adir[k]=id }} ]
			      [',']      
                            )+               {{ return (adir) }}

#    rule subgraph_stmt: ( 'subgraph|SUBGRAPH' id ['{' stmt_list '}']
#                        | ['subgraph|SUBGRAPH' [id]] '{' stmt_list '}' ) 

    rule subgraph_stmt: (
                          'subgraph|SUBGRAPH'
                          (
                               id ['{' stmt_list '}']
                             | '{' stmt_list '}'
                           )
                        | '{' stmt_list '}'
                        ) 

    rule edge_stmt:     (node_id | subgraph_stmt) edgeRHS [ attr_list ]
    
    rule edgeRHS: 	(  {{ list=[] }}
                       '--|->' 
                       (   node_id         {{ list.append (node_id) }}
                         | subgraph_stmt
                       ) 
                    )+   {{ return (list) }}

    rule node_stmt: node_id {{ nodes[node_id] = {} }} [ attr_list<<None>> {{ nodes[node_id] = attr_list }} ] {{ return (nodes) }}

    rule node_id:  	id  [ port ] {{ return (id) }}
    
    rule port: 	( port_location [ port_angle ]
	        | port_angle [ port_location ] )

    rule port_location:  ':' ( id
                	| '\\(' id ',' id '\\)' )

    rule port_angle: 	'@' id

        
    rule id:     ID     {{ return ID }}
               | STR    {{ return eval(STR, {"__builtins__": dict()}) }}
               | NUM    {{ return int(NUM) }}
