"""Shared compositor node helpers for the version adaptations."""


def first_output(node, *names):
    """Return the first output socket matching a name, else the first one."""
    for name in names:
        socket = node.outputs.get(name)
        if socket is not None:
            return socket
    return node.outputs[0]


def find_input(node, name, fallback_index=None):
    """Return an input socket by name, falling back to an index."""
    socket = node.inputs.get(name)
    if socket is not None:
        return socket
    if fallback_index is not None:
        return node.inputs[fallback_index]
    return node.inputs[0]


def set_input(node_tree, node, target, from_socket, fallback_index=None) -> bool:
    """Replace the links into an input socket with a single link."""
    socket = find_input(node, target, fallback_index)
    current = next(iter(socket.links), None)
    if current is not None and current.from_socket is from_socket:
        return False
    for link in list(socket.links):
        node_tree.links.remove(link)
    node_tree.links.new(from_socket, socket)
    return True


def clear_input(node_tree, node, target, fallback_index=None) -> bool:
    """Remove all links into an input socket."""
    socket = find_input(node, target, fallback_index)
    if not socket.links:
        return False
    for link in list(socket.links):
        node_tree.links.remove(link)
    return True
