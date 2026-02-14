#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CBDB JSON Search Tool

Search for keywords in specific node groups within CBDB API JSON files.

Usage:
    python cbdb_json_search.py -f <json_file> -n <node_name> -k <keyword> [-o <output_format>]

Examples:
    # Search for "Wang Anshi" in social associations
    python cbdb_json_search.py -f data.json -n PersonSocialAssociation -k "Wang Anshi"
    
    # Search for "father" in kinship info, output as JSON
    python cbdb_json_search.py -f data.json -n PersonKinshipInfo -k "father" -o json
    
    # List all aliases
    python cbdb_json_search.py -f data.json -n PersonAliases -k ""
"""

import json
import argparse
import os
import sys
from typing import Dict, Any, List, Optional, Tuple


# Node group to child node mapping
NODE_CHILD_MAP = {
    "BasicInfo": None,  # No child node, direct object
    "PersonSources": "Source",
    "PersonSourcesAs": "SourceAs",
    "PersonAliases": "Alias",
    "PersonAddresses": "Address",
    "PersonEntryInfo": "Entry",
    "PersonPostings": "Posting",
    "PersonSocialStatus": "SocialStatus",
    "PersonKinshipInfo": "Kinship",
    "PersonSocialAssociation": "Association",
    "PersonTexts": "Text"
}

# Node group descriptions (Chinese)
NODE_DESCRIPTIONS = {
    "BasicInfo": "Basic Information (Basic information)",
    "PersonSources": "Data Sources (Data sources)",
    "PersonSourcesAs": "Data Sources As (Data sources as)",
    "PersonAliases": "Aliases (Aliases)",
    "PersonAddresses": "Addresses (Related addresses)",
    "PersonEntryInfo": "Entry Info (Entry information)",
    "PersonPostings": "Postings (Official postings)",
    "PersonSocialStatus": "Social Status (Social status)",
    "PersonKinshipInfo": "Kinship Info (Family relationships)",
    "PersonSocialAssociation": "Social Association (Social relationships)",
    "PersonTexts": "Texts (Related texts)"
}


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON file and return parsed data.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data as dictionary
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_person_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract Person data from CBDB JSON structure.
    
    Args:
        data: Raw JSON data
        
    Returns:
        Person data dictionary
    """
    try:
        return data["Package"]["PersonAuthority"]["PersonInfo"]["Person"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"Invalid CBDB JSON structure: {e}")


def get_node_data(person_data: Dict[str, Any], node_name: str) -> Tuple[Any, Optional[str]]:
    """
    Get node data and its child node name.
    
    Args:
        person_data: Person data dictionary
        node_name: Name of the node group to retrieve
        
    Returns:
        Tuple of (node_data, child_node_name)
    """
    if node_name not in NODE_CHILD_MAP:
        raise ValueError(f"Unknown node name: {node_name}. Valid nodes: {list(NODE_CHILD_MAP.keys())}")
    
    if node_name not in person_data:
        return None, NODE_CHILD_MAP[node_name]
    
    return person_data[node_name], NODE_CHILD_MAP[node_name]


def search_in_dict(data: Dict[str, Any], keyword: str, case_sensitive: bool = False) -> bool:
    """
    Check if any value in dictionary contains the keyword.
    
    Args:
        data: Dictionary to search
        keyword: Keyword to search for
        case_sensitive: Whether search is case sensitive
        
    Returns:
        True if keyword found in any value
    """
    if not keyword:
        return True  # Empty keyword matches all
    
    for value in data.values():
        if value is None:
            continue
        value_str = str(value)
        if not case_sensitive:
            value_str = value_str.lower()
            keyword_lower = keyword.lower()
        else:
            keyword_lower = keyword
        
        if keyword_lower in value_str:
            return True
    
    return False


def search_node(node_data: Any, child_name: Optional[str], keyword: str, 
                case_sensitive: bool = False, limit: int = 0) -> List[Dict[str, Any]]:
    """
    Search for keyword in node data.
    
    Args:
        node_data: Node data (can be dict or contain child array)
        child_name: Name of child node array (None for BasicInfo)
        keyword: Keyword to search for
        case_sensitive: Whether search is case sensitive
        limit: Maximum number of results to return (0 = no limit)
        
    Returns:
        List of matching records
    """
    results = []
    
    if node_data is None:
        return results
    
    # BasicInfo is a direct object
    if child_name is None:
        if isinstance(node_data, dict):
            if search_in_dict(node_data, keyword, case_sensitive):
                results.append(node_data)
        return results
    
    # Other nodes have child arrays
    child_data = node_data.get(child_name, [])
    
    # Handle single dict (not in array)
    if isinstance(child_data, dict):
        if search_in_dict(child_data, keyword, case_sensitive):
            results.append(child_data)
        return results
    
    # Handle array
    if isinstance(child_data, list):
        for item in child_data:
            if isinstance(item, dict):
                if search_in_dict(item, keyword, case_sensitive):
                    results.append(item)
                    # Check limit
                    if limit > 0 and len(results) >= limit:
                        return results
    
    return results


def format_text_output(results: List[Dict[str, Any]], node_name: str, keyword: str, 
                       total_count: int = 0, limit: int = 0) -> str:
    """
    Format search results as human-readable text.
    
    Args:
        results: List of matching records
        node_name: Name of searched node
        keyword: Search keyword
        total_count: Total count of matching records (before limit)
        limit: Limit value used (0 = no limit)
        
    Returns:
        Formatted text string
    """
    if not results:
        return f"No results found for '{keyword}' in {node_name}"
    
    lines = []
    display_count = len(results)
    
    if total_count > display_count:
        lines.append(f"Found {total_count} record(s) in {node_name}, showing {display_count} (limit={limit})")
    else:
        lines.append(f"Found {display_count} record(s) in {node_name}")
    
    if keyword:
        lines.append(f"Keyword: {keyword}")
    lines.append("=" * 50)
    
    for i, record in enumerate(results, 1):
        lines.append(f"\nRecord {i}:")
        for key, value in record.items():
            if value:  # Only show non-empty values
                lines.append(f"  {key}: {value}")
    
    return "\n".join(lines)


def format_json_output(results: List[Dict[str, Any]], node_name: str, keyword: str) -> str:
    """
    Format search results as JSON.
    
    Args:
        results: List of matching records
        node_name: Name of searched node
        keyword: Search keyword
        
    Returns:
        JSON string
    """
    output = {
        "status": "success",
        "query": {
            "node": node_name,
            "keyword": keyword
        },
        "total": len(results),
        "results": results
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def list_available_nodes():
    """
    Print list of available node groups.
    """
    print("Available node groups:")
    print("-" * 50)
    for node, child in NODE_CHILD_MAP.items():
        desc = NODE_DESCRIPTIONS.get(node, "")
        child_info = f" -> {child}" if child else " (direct object)"
        print(f"  {node}{child_info}")
        print(f"    {desc}")
    print("-" * 50)


def main():
    """Command line interface entry point."""
    parser = argparse.ArgumentParser(
        description="CBDB JSON Search Tool - Search keywords in CBDB JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -f data.json -n PersonAliases -k "Wang"
  %(prog)s -f data.json -n PersonKinshipInfo -k "father" -o json
  %(prog)s -f data.json -n PersonPostings -k ""
  %(prog)s --list-nodes
        """
    )
    
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Path to JSON file"
    )
    parser.add_argument(
        "-n", "--node",
        type=str,
        help="Node group name to search"
    )
    parser.add_argument(
        "-k", "--keyword",
        type=str,
        default="",
        help="Keyword to search for (empty string returns all records)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "-c", "--case-sensitive",
        action="store_true",
        help="Case sensitive search"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=20,
        help="Maximum number of results to return (default: 20, use 0 for all)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Return all results (ignore limit)"
    )
    parser.add_argument(
        "--list-nodes",
        action="store_true",
        help="List available node groups"
    )
    
    args = parser.parse_args()
    
    # Handle --list-nodes
    if args.list_nodes:
        list_available_nodes()
        return
    
    # Handle --all: override limit to 0 (no limit)
    if args.all:
        args.limit = 0
    
    # Validate required arguments
    if not args.file or not args.node:
        parser.error("--file and --node are required (unless using --list-nodes)")
    
    try:
        # Load JSON file
        data = load_json_file(args.file)
        
        # Get person data
        person_data = get_person_data(data)
        
        # Get node data
        node_data, child_name = get_node_data(person_data, args.node)
        
        if node_data is None:
            print(f"Node '{args.node}' not found in JSON file")
            print(f"Available nodes: {list(person_data.keys())}")
            sys.exit(1)
        
        # Search
        # First get all results to count total, then apply limit
        all_results = search_node(node_data, child_name, args.keyword, args.case_sensitive, limit=0)
        total_count = len(all_results)
        
        # Apply limit
        if args.limit > 0:
            results = all_results[:args.limit]
        else:
            results = all_results
        
        # Output
        if args.output == "json":
            print(format_json_output(results, args.node, args.keyword))
        else:
            print(format_text_output(results, args.node, args.keyword, total_count, args.limit))
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file - {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()