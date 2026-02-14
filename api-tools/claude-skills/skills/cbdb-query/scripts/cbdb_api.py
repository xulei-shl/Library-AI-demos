#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CBDB API Python Client

China Biographical Database (CBDB) API wrapper
Supports querying person biographical information by ID or name

API Documentation: https://chinesecbdb.hsites.harvard.edu/cbdb-api
"""

import requests
import json
import argparse
import os
from datetime import datetime
from typing import Optional, Union, Dict, Any, List


class CBDBAPI:
    """
    CBDB API Client Class
    
    Used to query person information from China Biographical Database
    
    Attributes:
        base_url (str): API base URL
        timeout (int): Request timeout in seconds
    
    Example:
        >>> api = CBDBAPI()
        >>> # Query by ID
        >>> result = api.get_person_by_id(1762)  # Wang Anshi
        >>> # Query by name
        >>> result = api.get_person_by_name("Wang Anshi")
        >>> # Query by pinyin
        >>> result = api.get_person_by_name("wang anshi", pinyin=True)
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize CBDB API client
        
        Args:
            timeout: Request timeout in seconds, default 30 seconds
        """
        self.base_url = "https://cbdb.fas.harvard.edu/cbdbapi/person.php"
        self.timeout = timeout
    
    def get_person_by_id(
        self, 
        person_id: int, 
        output_format: str = "json"
    ) -> Union[Dict[str, Any], str]:
        """
        Query person biographical information by CBDB ID
        
        Args:
            person_id: CBDB person ID (e.g., 1762 for Wang Anshi)
            output_format: Output format, "json" or "html", default "json"
        
        Returns:
            If output_format is "json", returns parsed JSON dictionary
            If output_format is "html", returns HTML string
        
        Raises:
            ValueError: When person_id is invalid
            requests.RequestException: When network request fails
        
        Example:
            >>> api = CBDBAPI()
            >>> result = api.get_person_by_id(1762)
            >>> print(result)
        """
        if not isinstance(person_id, int) or person_id <= 0:
            raise ValueError("person_id must be a positive integer")
        
        params = {"id": person_id}
        
        if output_format.lower() == "json":
            params["o"] = "json"
        
        return self._make_request(params, output_format)
    
    def get_person_by_name(
        self, 
        name: str, 
        output_format: str = "json",
        pinyin: bool = False
    ) -> Union[Dict[str, Any], str]:
        """
        Query person biographical information by name
        
        Args:
            name: Person name (supports Chinese characters or pinyin)
            output_format: Output format, "json" or "html", default "json"
            pinyin: Whether this is a pinyin query, default False
        
        Returns:
            If output_format is "json", returns parsed JSON dictionary
            If output_format is "html", returns HTML string
        
        Raises:
            ValueError: When name is empty
            requests.RequestException: When network request fails
        
        Example:
            >>> api = CBDBAPI()
            >>> # Chinese character query
            >>> result = api.get_person_by_name("Wang Anshi")
            >>> # Pinyin query
            >>> result = api.get_person_by_name("wang anshi", pinyin=True)
        """
        if not name or not name.strip():
            raise ValueError("name cannot be empty")
        
        # requests automatically handles URL encoding, no manual encoding needed
        params = {"name": name.strip()}
        
        if output_format.lower() == "json":
            params["o"] = "json"
        
        return self._make_request(params, output_format)
    
    def _make_request(
        self, 
        params: Dict[str, Any], 
        output_format: str
    ) -> Union[Dict[str, Any], str]:
        """
        Send HTTP request to CBDB API
        
        Args:
            params: Request parameter dictionary
            output_format: Output format
        
        Returns:
            API response data
        
        Raises:
            requests.RequestException: When request fails
        """
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if output_format.lower() == "json":
                return response.json()
            else:
                return response.text
                
        except requests.exceptions.JSONDecodeError:
            # If JSON parsing fails, return raw text
            return response.text
        except requests.exceptions.RequestException as e:
            raise requests.RequestException(f"CBDB API request failed: {e}")


def search_person(
    identifier: Optional[Union[int, str]] = None,
    name: Optional[str] = None,
    output_format: str = "json"
) -> Union[Dict[str, Any], str]:
    """
    Convenience function: Search person information
    
    Can query by ID or name, prioritizes ID
    
    Args:
        identifier: CBDB person ID
        name: Person name
        output_format: Output format, "json" or "html"
    
    Returns:
        Person biographical information
    
    Example:
        >>> # Query by ID
        >>> result = search_person(identifier=1762)
        >>> # Query by name
        >>> result = search_person(name="Wang Anshi")
    """
    api = CBDBAPI()
    
    if identifier is not None:
        return api.get_person_by_id(identifier, output_format)
    elif name is not None:
        return api.get_person_by_name(name, output_format)
    else:
        raise ValueError("Must provide identifier or name parameter")


def extract_summary(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract summary information from raw CBDB API response
    
    Args:
        raw_data: Raw API response containing Package structure
        
    Returns:
        Simplified summary dictionary with key person information
    """
    summary = {
        "status": "success",
        "query": {},
        "timestamp": datetime.now().isoformat(),
        "data": {
            "person": {},
            "summary": "",
            "aliases": [],
            "career": [],
            "addresses": [],
            "writings": []
        }
    }
    
    try:
        package = raw_data.get("Package", {})
        person_info = package.get("PersonAuthority", {}).get("PersonInfo", {}).get("Person", {})
        
        # Extract basic info
        basic_info = person_info.get("BasicInfo", {})
        if basic_info:
            summary["data"]["person"] = {
                "id": basic_info.get("PersonId", ""),
                "cbdb_id": basic_info.get("PersonId", ""),
                "name": basic_info.get("EngName", ""),
                "chinese_name": basic_info.get("ChName", ""),
                "birth_year": basic_info.get("YearBirth", ""),
                "death_year": basic_info.get("YearDeath", ""),
                "age": basic_info.get("YearsLived", ""),
                "gender": "male" if basic_info.get("Gender") == "0" else "female",
                "dynasty": basic_info.get("Dynasty", ""),
                "dynasty_id": basic_info.get("DynastyId", ""),
                "index_addr": basic_info.get("IndexAddr", ""),
                "index_addr_id": basic_info.get("IndexAddrId", ""),
                "notes": basic_info.get("Notes", "")
            }
        
        # Extract aliases
        aliases = person_info.get("PersonAliases", {}).get("Alias", [])
        if isinstance(aliases, dict):
            aliases = [aliases]
        summary["data"]["aliases"] = [
            {
                "type": a.get("AliasType", ""),
                "name": a.get("AliasName", "")
            }
            for a in aliases if a.get("AliasName")
        ]
        
        # Extract career/postings
        postings = person_info.get("PersonPostings", {}).get("Posting", [])
        if isinstance(postings, dict):
            postings = [postings]
        summary["data"]["career"] = [
            {
                "office": p.get("OfficeName", ""),
                "location": p.get("AddrName", ""),
                "start_year": p.get("FirstYear", ""),
                "end_year": p.get("LastYear", "")
            }
            for p in postings[:20]  # Limit to first 20 entries
            if p.get("OfficeName")
        ]
        
        # Extract addresses
        addresses = person_info.get("PersonAddresses", {}).get("Address", [])
        if isinstance(addresses, dict):
            addresses = [addresses]
        summary["data"]["addresses"] = [
            {
                "type": a.get("AddrType", ""),
                "name": a.get("AddrName", "")
            }
            for a in addresses if a.get("AddrName")
        ]
        
        # Extract writings/texts (PersonTexts)
        texts = person_info.get("PersonTexts", {}).get("Text", [])
        if isinstance(texts, dict):
            texts = [texts]
        summary["data"]["writings"] = [
            {
                "text_name": t.get("TextName", ""),
                "year": t.get("Year", ""),
                "role": t.get("Role", "")
            }
            for t in texts[:20]  # Limit to first 20 entries
            if t.get("TextName")
        ]
        
    except Exception as e:
        summary["extraction_error"] = str(e)
    
    return summary


def save_results(
    raw_data: Dict[str, Any],
    identifier: str,
    output_dir: str = "temps/cbdb"
) -> Dict[str, str]:
    """
    Save both raw and summary JSON files
    
    Args:
        raw_data: Raw API response
        identifier: Person name or ID for filename
        output_dir: Directory to save files
        
    Returns:
        Dictionary with paths to saved files
    """
    # Create output directory if not exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean identifier for filename (remove spaces and special chars)
    safe_identifier = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(identifier))
    
    # File paths
    raw_filename = f"cbdb_raw_{safe_identifier}_{timestamp}.json"
    summary_filename = f"cbdb_summary_{safe_identifier}_{timestamp}.json"
    
    raw_path = os.path.join(output_dir, raw_filename)
    summary_path = os.path.join(output_dir, summary_filename)
    
    # Save raw data
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    
    # Extract and save summary
    summary = extract_summary(raw_data)
    summary["query"] = {"identifier": identifier}
    
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    return {
        "raw_file": raw_path,
        "summary_file": summary_path
    }


def main():
    """Command line interface entry point"""
    parser = argparse.ArgumentParser(
        description="CBDB API Client - Query China Biographical Database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --name "Wang Anshi"        # Query by Chinese name
  %(prog)s --id 1762                   # Query by CBDB ID
  %(prog)s --name "wang anshi" --pinyin  # Query by pinyin
  %(prog)s --name "Wang Anshi" --save  # Query and save to files
        """
    )
    
    parser.add_argument(
        "--name", 
        type=str, 
        help="Person name to search (Chinese characters or pinyin)"
    )
    parser.add_argument(
        "--id", 
        type=int, 
        help="CBDB person ID"
    )
    parser.add_argument(
        "--pinyin", 
        action="store_true", 
        help="Treat name as pinyin (use with --name)"
    )
    parser.add_argument(
        "--format", 
        choices=["json", "html"], 
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--save", 
        action="store_true",
        help="Save results to JSON files (both raw and summary)"
    )
    parser.add_argument(
        "--output-dir", 
        type=str,
        default="temps/cbdb",
        help="Output directory for saved files (default: temps/cbdb)"
    )
    
    args = parser.parse_args()
    
    if not args.name and not args.id:
        parser.error("Please provide --name or --id")
    
    api = CBDBAPI()
    
    try:
        if args.id:
            result = api.get_person_by_id(args.id, args.format)
            identifier = str(args.id)
        else:
            result = api.get_person_by_name(args.name, args.format, args.pinyin)
            identifier = args.name
        
        if isinstance(result, dict):
            if args.save:
                # Save both raw and summary files
                paths = save_results(result, identifier, args.output_dir)
                print(f"Raw data saved to: {paths['raw_file']}")
                print(f"Summary saved to: {paths['summary_file']}")
                print("\n--- Summary Preview ---")
                summary = extract_summary(result)
                print(json.dumps(summary, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)
            
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
    except requests.RequestException as e:
        print(f"Network Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()