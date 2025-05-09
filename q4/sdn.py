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

# this is 
link_stats = {}

def find_link_stats(a, b):
    if (a, b) in link_stats: return link_stats[(a, b)]
    if (b, a) in link_stats: return link_stats[(b, a)]
    return None

link_stats_patches = []
def draw_link_stats():
    global link_stats_patches
    for i, patch in enumerate(link_stats_patches):
        patch.remove()

    link_stats_patches = []

    for stats in link_stats.values():
        src = all_nodes[stats.a]
        dst = all_nodes[stats.b]
        center_x = (src.x + dst.x) / 2.0
        center_y = (src.y + dst.y) / 2.0
        circle = Circle((center_x, center_y), 0.25, color='white', zorder=3)
        text = ax.text(center_x, center_y, stats.times_used, ha='center', va='center', color='black', fontsize=12, zorder=4)
        ax.add_patch(circle)
        link_stats_patches.append(circle)
        link_stats_patches.append(text)


# simple link statistics tracker, used for routing decisions.
# i added this a little later on in the project,
# so the node code mostly still uses indices of other nodes to handle links.
class NetworkLink:
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.times_used = 0


# a node in the network.
class NetworkNode:
    def __init__(self, name, x, y):
        self.name = name
        self.x = x
        self.y = y

        # indices of other nodes linked to us
        self.links = []

        self.fwd_table = []
        self.fwd_distances = []

        self.node_icon = Circle((x, y), 0.75, color='blue', zorder=1)
        ax.add_patch(self.node_icon)
        self.text = ax.text(x, y, self.name, ha='center', va='center', color='black', fontsize=12, zorder=2)

        self.link_patches = []

    def destroy(self):
        self.node_icon.remove()
        self.text.remove()

        for i, patch in enumerate(self.link_patches):
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
                    # for this simple implementation, all nodes are spaced 1 unit apart (despite what the graph UI shows).
                    test_dist = shortest_dist[cur] + 1

                    # if this distance is smaller than the one we already know, it's a better path.
                    if test_dist < shortest_dist[neighbor_index]:
                        shortest_dist[neighbor_index] = test_dist
                        prev[neighbor_index] = cur
        
        
        # Now that we have the shortest distance to each node,
        # update the forwarding table.
        self.fwd_table = [None] * len(all_nodes)
        self.fwd_distances = shortest_dist
        for node_index in range(len(all_nodes)):
            if node_index == self.index:
                continue
            
            # Calc the path to this node.
            path = self.get_path_to_node(prev, node_index)
            if path and len(path) != 0:
                self.fwd_table[node_index] = self.links.index(path[0])
                # self.fwd_table[node_index] = path


    def get_ideal_interface(self, dst):
        return self.fwd_table[dst]

    # Choose an interface for the packet to exit from.
    def choose_exit_interface(self, dst, high_priority):
        global all_nodes
        ideal_iface = self.get_ideal_interface(dst)
        if ideal_iface == None:
            return None
        
        iface_candidates = []
        iface_costs = []

        iface_candidates.append(ideal_iface)
        iface_costs.append(self.fwd_distances[dst])

        # Load balance if we're allowed.
        if not high_priority:
            for i, link in enumerate(self.links):
                if i == ideal_iface:
                    continue
                
                neighbor = all_nodes[link]
                # if the neighbor node has a path to the destination that doesn't just pass back through us,
                # it's probably a good candidate for load balancing.
                # This is just a prototype, real SDNs have more complex forwarding tables that can handle multiple candidates.
                neighbor_ideal = neighbor.get_ideal_interface(dst)
                if neighbor_ideal != None and neighbor.links[neighbor_ideal] != self.index:
                    iface_candidates.append(i)
                    # add 1 here to represent the additional hop to this neighbor.
                    iface_costs.append(1 + neighbor.fwd_distances[dst])

        # ideally this would evaluate cost aswell, but right now it's just hot potato
        link_weights = [-1] * len(self.links)

        # -1 signifies this link is not a candidate.
        # If a link is used 4 times, it'll start to balance to other links.
        for i, iface in enumerate(iface_candidates):
            stats = find_link_stats(self.index, self.links[iface])
            link_weights[iface] = stats.times_used * 0.25 + iface_costs[i]
        
        return link_weights



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

    draw_link_stats()
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
    if b in all_nodes[a].links or a in all_nodes[b].links:
        return
    
    all_nodes[a].links.append(b)
    all_nodes[b].links.append(a)
    link_stats[(a, b)] = NetworkLink(a, b)


def unlink_nodes(a, b):
    all_nodes[a].links.remove(b)
    all_nodes[b].links.remove(a)
    if (a, b) in link_stats: del link_stats[(a, b)]
    if (b, a) in link_stats: del link_stats[(b, a)]


def create_test_network():
    add_node("R0", -2, -2)
    add_node("R1", 2, -2)
    add_node("R2", -2, 2)
    add_node("R3", 3, 0)
    add_node("R4", 3, 3)
    add_node("R5", 0, 0.5)
    add_node("R6", 0, 3)

    link_nodes(0, 1)
    link_nodes(0, 2)
    link_nodes(1, 3)

    # make some alternate routes for R2 <-> R3 to test load balancing
    link_nodes(2, 6)
    link_nodes(6, 4)
    link_nodes(4, 3)

    link_nodes(2, 5)
    link_nodes(5, 3)

    update_network_topology()

def simulate_packet(src, dst, high_priority):
    print(f'Routing packet from {args[1]} -> {args[2]}')
    while src != dst:
        print(f'{all_nodes[src].name}:')
        link_weights = all_nodes[src].choose_exit_interface(dst, high_priority)
        if link_weights == None:
            print(f'No path to destination!')
            break
        
        # Pick the smallest weighted link that isn't 0 in order to load balance.
        smallest = MAX_DIST
        best_iface = -1
        print('\tLink weights (choosing smallest):')
        for iface, weight in enumerate(link_weights):
            if weight == -1:
                continue
    
            iface_dest = all_nodes[src].links[iface]
            print(f'\t\t{iface} ({all_nodes[iface_dest].name}): {weight}')

            if weight < smallest:
                smallest = weight
                best_iface = iface

        if best_iface == -1:
            print('No link found!')
            break
        
        new_src = all_nodes[src].links[best_iface]

        # Update the link stats.
        stats = find_link_stats(src, new_src)
        if stats != None:
            stats.times_used += 1

        src = new_src
        print(f'\tSending packet through interface {best_iface} ({all_nodes[src].name})...')
    print('Finished!')

    # Redraw the link stats.
    draw_link_stats()
    plt.draw()


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
    
    # simulate name0 name1
    # simulate a packet flowing between two nodes.
    if args[0] == 'simulate':
        src = get_node_index(args[1])
        dst = get_node_index(args[2])
        if src != -1 and dst != -1:
            simulate_packet(src, dst, False)
        return

    # simulate_high_priority name0 name1
    # simulate a high-priority packet between two nodes (takes the shortest route no matter what, no load balancing allowed).
    if args[0] == 'simulate_high_priority':
        src = get_node_index(args[1])
        dst = get_node_index(args[2])
        if src != -1 and dst != -1:
            simulate_packet(src, dst, True)
        return


# Run simulator
create_test_network()
plt.show(block=False)

while True:
    cmd = input('> ')
    if len(cmd) == 0:
        continue

    args = cmd.split(' ')

    # quit
    # stops the program.
    if args[0] == 'quit':
        break

    try:
        handle_command(args)
    except Exception as e:
        print(f'Error: {e}\n')


