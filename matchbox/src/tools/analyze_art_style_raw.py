# -*- coding: utf-8 -*-
"""
Art Style Raw Data Analysis Tool

This script analyzes the art_style_raw field from pipeline outputs to identify
high-frequency free-form style terms that could be candidates for inclusion
in the standardized vocabulary.

Usage:
    python -m src.tools.analyze_art_style_raw [--input-dir PATH] [--threshold FLOAT]

Args:
    --input-dir: Directory containing JSON output files (default: runtime/outputs)
    --threshold: Minimum frequency percentage for candidate terms (default: 5.0)
"""
import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple


def load_json_files(input_dir: str) -> List[Dict]:
    """
    Load all JSON files from the specified directory.

    Args:
        input_dir: Path to directory containing JSON output files

    Returns:
        List of parsed JSON objects
    """
    json_files = []
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"Warning: Input directory '{input_dir}' does not exist")
        return json_files

    for file_path in input_path.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                json_files.append(data)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    return json_files


def extract_art_style_raw_terms(json_files: List[Dict]) -> List[str]:
    """
    Extract all art_style_raw terms from JSON files.

    Args:
        json_files: List of parsed JSON objects

    Returns:
        List of art style raw terms (flattened)
    """
    terms = []

    for data in json_files:
        art_style_raw = data.get("art_style_raw")

        if art_style_raw is not None:
            if isinstance(art_style_raw, list):
                # Flatten list of terms
                terms.extend([term for term in art_style_raw if term])
            elif isinstance(art_style_raw, str):
                # Single term as string
                terms.append(art_style_raw)

    return terms


def analyze_term_frequency(terms: List[str], total_records: int, threshold: float = 5.0) -> Tuple[Counter, List[Tuple[str, int, float]]]:
    """
    Analyze frequency of art_style_raw terms.

    Args:
        terms: List of all extracted terms
        total_records: Total number of records processed
        threshold: Minimum frequency percentage for candidates

    Returns:
        Tuple of (Counter object, list of candidate terms with stats)
    """
    term_counts = Counter(terms)
    candidates = []

    for term, count in term_counts.most_common():
        percentage = (count / total_records) * 100 if total_records > 0 else 0
        if percentage >= threshold:
            candidates.append((term, count, percentage))

    return term_counts, candidates


def find_example_paths(json_files: List[Dict], term: str, max_examples: int = 3) -> List[str]:
    """
    Find example image paths for a given art_style_raw term.

    Args:
        json_files: List of parsed JSON objects
        term: Art style term to search for
        max_examples: Maximum number of example paths to return

    Returns:
        List of example file paths (IDs)
    """
    examples = []

    for data in json_files:
        if len(examples) >= max_examples:
            break

        art_style_raw = data.get("art_style_raw")

        if art_style_raw is not None:
            if isinstance(art_style_raw, list) and term in art_style_raw:
                examples.append(data.get("id", "unknown"))
            elif isinstance(art_style_raw, str) and art_style_raw == term:
                examples.append(data.get("id", "unknown"))

    return examples


def analyze_other_category(json_files: List[Dict]) -> Tuple[int, float]:
    """
    Analyze the usage of the "其他" (Other) category.

    Args:
        json_files: List of parsed JSON objects

    Returns:
        Tuple of (count of "其他" usage, percentage)
    """
    total = len(json_files)
    other_count = 0

    for data in json_files:
        art_style = data.get("art_style")
        if art_style is not None:
            if isinstance(art_style, list) and "其他" in art_style:
                other_count += 1
            elif isinstance(art_style, str) and art_style == "其他":
                other_count += 1

    percentage = (other_count / total) * 100 if total > 0 else 0
    return other_count, percentage


def generate_report(
    json_files: List[Dict],
    term_counts: Counter,
    candidates: List[Tuple[str, int, float]],
    threshold: float
) -> str:
    """
    Generate a formatted analysis report.

    Args:
        json_files: List of parsed JSON objects
        term_counts: Counter of all term frequencies
        candidates: List of candidate terms above threshold
        threshold: Frequency threshold used

    Returns:
        Formatted report string
    """
    total_records = len(json_files)
    total_terms = len(term_counts)
    other_count, other_percentage = analyze_other_category(json_files)

    report_lines = [
        "=" * 80,
        "艺术风格原始数据分析报告 (Art Style Raw Data Analysis Report)",
        "=" * 80,
        "",
        f"总记录数 (Total Records): {total_records}",
        f"唯一艺术风格术语数 (Unique Terms): {total_terms}",
        f"\"其他\"类别使用次数 (\"Other\" Category Usage): {other_count} ({other_percentage:.2f}%)",
        f"频率阈值 (Frequency Threshold): {threshold}%",
        "",
        "=" * 80,
        f"高频候选术语 (High-Frequency Candidate Terms, >= {threshold}%)",
        "=" * 80,
        ""
    ]

    if candidates:
        report_lines.append(f"{'术语 (Term)':<30} {'次数 (Count)':<15} {'占比 (Percentage)':<20} {'示例 (Examples)'}")
        report_lines.append("-" * 80)

        for term, count, percentage in candidates:
            examples = find_example_paths(json_files, term, max_examples=3)
            examples_str = ", ".join(examples[:3])
            report_lines.append(f"{term:<30} {count:<15} {percentage:>6.2f}%            {examples_str}")
    else:
        report_lines.append(f"未发现超过 {threshold}% 阈值的候选术语")
        report_lines.append("(No candidate terms found above threshold)")

    report_lines.extend([
        "",
        "=" * 80,
        "完整术语频率分布 (Full Term Frequency Distribution)",
        "=" * 80,
        ""
    ])

    if term_counts:
        report_lines.append(f"{'术语 (Term)':<30} {'次数 (Count)':<15} {'占比 (Percentage)'}")
        report_lines.append("-" * 80)

        for term, count in term_counts.most_common():
            percentage = (count / total_records) * 100 if total_records > 0 else 0
            report_lines.append(f"{term:<30} {count:<15} {percentage:>6.2f}%")
    else:
        report_lines.append("无 art_style_raw 数据")
        report_lines.append("(No art_style_raw data found)")

    report_lines.extend([
        "",
        "=" * 80,
        "建议 (Recommendations)",
        "=" * 80,
        ""
    ])

    if candidates:
        report_lines.append("以下术语可能适合纳入标准艺术风格词表:")
        report_lines.append("(The following terms may be suitable for inclusion in the standard vocabulary:)")
        report_lines.append("")
        for term, count, percentage in candidates[:5]:  # Top 5
            report_lines.append(f"  - {term} (出现 {count} 次, {percentage:.2f}%)")

    if other_percentage > 20:
        report_lines.append("")
        report_lines.append(f"注意: \"其他\"类别使用率较高 ({other_percentage:.2f}%),")
        report_lines.append("建议检查是否需要扩展标准词表以提高覆盖度。")
        report_lines.append(f"(Note: High usage of \"Other\" category ({other_percentage:.2f}%),")
        report_lines.append("consider expanding the standard vocabulary for better coverage.)")

    report_lines.append("")
    return "\n".join(report_lines)


def main():
    """Main entry point for the analysis tool."""
    parser = argparse.ArgumentParser(
        description="Analyze art_style_raw field data for vocabulary evolution"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="runtime/outputs",
        help="Directory containing JSON output files (default: runtime/outputs)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Minimum frequency percentage for candidate terms (default: 5.0)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for the report (default: print to console)"
    )

    args = parser.parse_args()

    print(f"Loading JSON files from: {args.input_dir}")
    json_files = load_json_files(args.input_dir)

    if not json_files:
        print("No JSON files found or loaded. Exiting.")
        return

    print(f"Loaded {len(json_files)} JSON files")
    print("Extracting art_style_raw terms...")

    terms = extract_art_style_raw_terms(json_files)
    print(f"Found {len(terms)} total art_style_raw term occurrences")

    print("Analyzing term frequency...")
    term_counts, candidates = analyze_term_frequency(terms, len(json_files), args.threshold)

    print("Generating report...")
    report = generate_report(json_files, term_counts, candidates, args.threshold)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
