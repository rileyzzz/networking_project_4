# sofware-defined network controller simulator
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

# create visualization graph
fig, ax = plt.subplots()
ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)
ax.set_aspect('equal')

# network topology stuff
all_nodes = []

# maximum distance constant for dijkstra's
MAX_DIST = 1000

class NetworkNode:
    def __init__(self, name, x, y):
        self.name = name
        self.x = x
        self.y = y

        # indices of other nodes linked to us
        self.links = []

        self.fwd_table = []

        self.node_icon = Circle((x, y), 0.75, color='blue', zorder=1)
        ax.add_patch(self.node_icon)
        self.text = ax.text(x, y, self.name, ha='center', va='center', color='black', fontsize=12, zorder=2)

        self.link_patches = []
        self.link_stats = []

    def destroy(self):
        self.node_icon.remove()
        self.text.remove()

        for i, patch in enumerate(self.link_patches):
            patch.remove()

        for i, patch in enumerate(self.link_stats):
            patch.remove()   

    # this will draw duplicate links (A -> B and B -> A on top of eachother), but that's ok since this is only a prototype.
    def redraw_links(self):
        global all_nodes
        for i, patch in enumerate(self.link_patches):
            patch.remove()
        
        self.link_patches = []
        for i, link in enumerate(self.links):
            dest = all_nodes[link]
            # print(f'drawing link {self.index} ({self.x}, {self.y}) -> {link} ({dest.x}, {dest.y})')
            line = ax.plot([self.x, dest.x], [self.y, dest.y], color='black', zorder=0)
            self.link_patches.append(line[0])

    def redraw_stats(self):
        for i, patch in enumerate(self.link_stats):
            patch.remove()

        self.link_stats = []

        for i, link in enumerate(self.links):
            dest = all_nodes[link]
            center_x = (self.x + dest.x) / 2.0
            center_y = (self.y + dest.y) / 2.0
            # text = ax.text(center_x, center_y, self.name, ha='left', va='bottom', color='black', fontsize=12, zorder=2)
            # self.link_stats.append(text)

    def get_path_to_node(self, prev, target_node):
        path = []
        cur = target_node
        while cur != None:
            path.insert(0, cur)
            cur = prev[cur]
            if cur == self.index:
                # path complete
                return path
            
        # no viable path!
        return None
    
    def calc_shortest_paths(self):
        global all_nodes

        visited = [False] * len(all_nodes)
        shortest_dist = [MAX_DIST] * len(all_nodes)
        prev = [None] * len(all_nodes)

        shortest_dist[self.index] = 0

        while True:
            cur = -1
            cur_dist = MAX_DIST

            # get the unvisited vertex with the smallest distance.
            for node_index in range(len(all_nodes)):
                if not visited[node_index] and shortest_dist[node_index] < cur_dist:
                    cur = node_index
                    cur_dist = shortest_dist[node_index]

            # break when all nodes have been visited.
            if cur == -1:
                break
                                
            # Mark us as visited
            visited[cur] = True

            # get neighbors at this vertex.
            neighbors = all_nodes[cur].links
            for i, neighbor_index in enumerate(neighbors):
                if not visited[neighbor_index]:
                    # calc dist from current node.
                    # for this simple implementation, all nodes are spaced 1 unit apart.
                    test_dist = shortest_dist[cur] + 1

                    # if this distance is smaller than the one we already know, it's a better path.
                    if test_dist < shortest_dist[neighbor_index]:
                        shortest_dist[neighbor_index] = test_dist
                        prev[neighbor_index] = cur
        
        
        # Now that we have the shortest distance to each node,
        # update the forwarding table.
        self.fwd_table = [None] * len(all_nodes)
        for node_index in range(len(all_nodes)):
            if node_index == self.index:
                continue
            
            # Calc the path to this node.
            path = self.get_path_to_node(prev, node_index)
            if path and len(path) != 0:
                self.fwd_table[node_index] = self.links.index(path[0])
                # self.fwd_table[node_index] = path


    def print_topology(self):
        global all_nodes
        print(f'Links for node {self.name}:')
        for i, link in enumerate(self.links):
            print(f'\tinterface {i}: {all_nodes[link].name}')

        print(f'FWD table for node {self.name}:')
        for node_index in range(len(all_nodes)):
            interface_index = self.fwd_table[node_index]
            detail_str = ''
            if interface_index != None:
                interface_node = self.links[interface_index]
                detail_str = f'(node {all_nodes[interface_node].name})'

            print(f'\t{all_nodes[node_index].name} -> interface {interface_index} {detail_str}')




# run dijkstra's on the network every time the network topology changes
def update_network_topology():
    global all_nodes
    for node_index in range(len(all_nodes)):
        all_nodes[node_index].calc_shortest_paths()
        all_nodes[node_index].redraw_links()

    plt.draw()

def get_node_index(name):
    for i, node in enumerate(all_nodes):
        if node.name == name:
            return i
        
    return -1

def add_node(name, x, y):
    global all_nodes

    node = NetworkNode(name, x, y)
    node.index = len(all_nodes)
    all_nodes.append(node)

def remove_node(name):
    global all_nodes

    updated_nodes = []
    removed_index = -1
    for i, node in enumerate(all_nodes):
        if node.name == name:
            removed_index = i
            node.destroy()
            continue
        updated_nodes.append(node)

    if removed_index == -1:
        return
    
    old_nodes = all_nodes
    all_nodes = updated_nodes

    # update node indices.
    for i, node in enumerate(all_nodes):
        node.index = i
    
    # Update link indices.
    for i, node in enumerate(all_nodes):
        if removed_index in node.links: node.links.remove(removed_index)

        # fixup indices.
        for i in range(len(node.links)):
            node.links[i] = old_nodes[node.links[i]].index


def link_nodes(a, b):
    all_nodes[a].links.append(b)
    all_nodes[b].links.append(a)


def unlink_nodes(a, b):
    all_nodes[a].links.remove(b)
    all_nodes[b].links.remove(a)


def create_test_network():
    add_node("R0", -2, -2)
    add_node("R1", 2, -2)
    add_node("R2", -2, 2)
    add_node("R3", 3, 0)

    link_nodes(0, 1)
    link_nodes(0, 2)
    link_nodes(1, 3)

    update_network_topology()


create_test_network()

plt.show(block=False)

def handle_command(args):
    global all_nodes

    # add name x y
    # add a node named 'name' at position (x, y)
    if args[0] == 'add':
        name = args[1]
        x = int(args[2])
        y = int(args[3])
        add_node(name, x, y)
        update_network_topology()
        return
    
    # remove name
    # remove a node by its name.
    if args[0] == 'rem':
        name = args[1]
        remove_node(name)
        update_network_topology()
        return
    
    # link name0 name1
    # link two nodes by name.
    if args[0] == 'link':
        l0 = get_node_index(args[1])
        l1 = get_node_index(args[2])
        if l0 != -1 and l1 != -1:
            link_nodes(l0, l1)
            update_network_topology()
        return
    
    # unlink name0 name1
    # unlink two nodes by name. will throw an exception if the nodes aren't actually linked.
    if args[0] == 'unlink':
        l0 = get_node_index(args[1])
        l1 = get_node_index(args[2])
        if l0 != -1 and l1 != -1:
            unlink_nodes(l0, l1)
            update_network_topology()
        return
    
    if args[0] == 'print':
        node = get_node_index(args[1])
        if node != -1:
            all_nodes[node].print_topology()
        return
    
while True:
    cmd = input('> ')
    if len(cmd) == 0:
        continue

    args = cmd.split(' ')

    # quit
    # stops the program.
    if args[0] == 'quit':
        break

    handle_command(args)
    # try:
    #     handle_command(args)
    # except Exception as e:
    #     print(f'Error: {e}\n')


