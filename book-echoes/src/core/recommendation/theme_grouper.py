import pandas as pd
from typing import Dict, List
from .config import normalize_theme, MAX_BATCH_SIZE, even_batches

def group_by_theme(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    groups: Dict[str, List[int]] = {}
    for idx, row in df.iterrows():
        theme = normalize_theme(str(row.get('索书号', '')))
        groups.setdefault(theme, []).append(idx)
    result: Dict[str, pd.DataFrame] = {}
    for theme, indices in groups.items():
        result[theme] = df.loc[indices]
    return result

def split_batches(items: List[Dict], max_batch_size: int = MAX_BATCH_SIZE) -> List[List[Dict]]:
    n = len(items)
    if n == 0:
        return []
    sizes = even_batches(n, max_batch_size)
    batches: List[List[Dict]] = []
    start = 0
    for size in sizes:
        end = start + size
        batches.append(items[start:end])
        start = end
    return batches