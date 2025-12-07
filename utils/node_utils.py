"""
Utility functions for Blender node operations.

Contains helpers for:
- Shader Nodes (Material Node Trees)
- Geometry Nodes (Modifiers)
"""

import bpy
from typing import Any, Optional, List


def find_node_group(
    node_tree: bpy.types.NodeTree, 
    group_name: str,
    exact_match: bool = False
) -> Optional[bpy.types.Node]:
    """
    Find a node group in the node tree.
    
    Args:
        node_tree: The node tree to search in
        group_name: Name of the node group to find
        exact_match: If True, only accept exact name matches
        
    Returns:
        The found node or None
    """
    for node in node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            # Exact match
            if node.node_tree.name == group_name:
                return node
            # Partial match as fallback (if not exact_match)
            if not exact_match:
                if group_name in node.node_tree.name or node.node_tree.name in group_name:
                    return node
    return None


def find_all_node_groups(
    node_tree: bpy.types.NodeTree,
    group_name: str = None
) -> List[bpy.types.Node]:
    """
    Find all node groups in the node tree.
    
    Args:
        node_tree: The node tree to search in
        group_name: Optional - filter by this name (partial match)
        
    Returns:
        List of all found group nodes
    """
    groups = []
    for node in node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            if group_name is None:
                groups.append(node)
            elif group_name in node.node_tree.name or node.node_tree.name in group_name:
                groups.append(node)
    return groups


def set_node_input(
    node: bpy.types.Node, 
    input_name: str, 
    value: Any,
    remove_links: bool = False
) -> bool:
    """
    Set an input value of a shader node.
    
    Args:
        node: The node whose input should be set
        input_name: Name of the input
        value: The value to set
        remove_links: If True, existing links to the input are removed.
                      WARNING: Set to False during rendering to avoid crashes!
        
    Returns:
        True if successful, False otherwise
    """
    # Try exact match
    inp = None
    if input_name in node.inputs:
        inp = node.inputs[input_name]
    else:
        # Case-insensitive search as fallback
        for i in node.inputs:
            if i.name.lower() == input_name.lower():
                inp = i
                break
    
    if inp is None:
        return False
    
    # Remove existing links if present (disabled by default to avoid render crashes)
    if remove_links:
        node_tree = node.id_data
        for link in list(node_tree.links):
            if link.to_socket == inp:
                node_tree.links.remove(link)
                break
    
    # Set value
    inp.default_value = value
    return True


def get_node_input(node: bpy.types.Node, input_name: str) -> Optional[Any]:
    """
    Read the current value of a node input.
    
    Args:
        node: The node whose input should be read
        input_name: Name of the input
        
    Returns:
        The current value or None if not found
    """
    if input_name in node.inputs:
        return node.inputs[input_name].default_value
    
    # Case-insensitive Suche
    for inp in node.inputs:
        if inp.name.lower() == input_name.lower():
            return inp.default_value
    
    return None


def set_geometry_node_input(
    obj: bpy.types.Object, 
    modifier_name: str, 
    input_name: str, 
    value: Any
) -> bool:
    """
    Set an input value of a Geometry Nodes modifier.
    
    Args:
        obj: The object with the modifier
        modifier_name: Name of the Geometry Nodes modifier
        input_name: Name or identifier of the input (e.g. "Seed" or "Socket_1")
        value: The value to set
        
    Returns:
        True if successful, False otherwise
        
    Note:
        This function first tries to find the input by display name,
        then falls back to using the name as identifier directly.
    """
    modifier = obj.modifiers.get(modifier_name)
    if not modifier or modifier.type != 'NODES':
        return False
    
    if not modifier.node_group:
        return False
    
    # Find the identifier for the given input name
    identifier = None
    for item in modifier.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
            if item.name == input_name:
                identifier = item.identifier
                break
    
    # Fallback: try using input_name directly as identifier
    if identifier is None:
        identifier = input_name
    
    try:
        modifier[identifier] = value
        return True
    except (KeyError, TypeError):
        return False


def get_geometry_node_input(
    obj: bpy.types.Object, 
    modifier_name: str, 
    input_identifier: str
) -> Optional[Any]:
    """
    Read an input value of a Geometry Nodes modifier.
    
    Args:
        obj: The object with the modifier
        modifier_name: Name of the Geometry Nodes modifier
        input_identifier: Identifier of the input
        
    Returns:
        The current value or None if not found
    """
    modifier = obj.modifiers.get(modifier_name)
    if not modifier or modifier.type != 'NODES':
        return None
    
    try:
        return modifier[input_identifier]
    except (KeyError, TypeError):
        return None


def list_geometry_node_inputs(
    obj: bpy.types.Object, 
    modifier_name: str
) -> List[str]:
    """
    List all available input identifiers of a Geometry Nodes modifier.
    
    Args:
        obj: The object with the modifier
        modifier_name: Name of the Geometry Nodes modifier
        
    Returns:
        List of input identifiers
    """
    modifier = obj.modifiers.get(modifier_name)
    if not modifier or modifier.type != 'NODES' or not modifier.node_group:
        return []
    
    inputs = []
    for item in modifier.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
            inputs.append(item.identifier)
    
    return inputs
