"""Functions to retrieve the existing data for given input parameters if avaliable,
otherwise signal to fetch new data.

Copyright 2024 Daniil Pomogaev
SPDX-License-Identifier: Apache-2.0
"""

import os
import hashlib
import pandas as pd
from pathlib import Path

def hash_parameters(
    k_files: list[str]|str,
    a_files: list[str],
    imputation: str,
    f_format: str,
) -> str:
    """Create a hash from input parameters."""
    hash_str = f"{sorted(k_files)}{sorted(a_files)}{imputation}{f_format}"
    return hashlib.md5(hash_str.encode(), usedforsecurity=False).hexdigest()[:16]

def check_existing_data(
    hash: str,
    data_folder: str,
) -> pd.DataFrame | None:
    """Check if data for given parameters is already present."""
    if not os.path.exists(data_folder):
        return None
    data_file = Path(data_folder) / f"{hash}.csv"
    if not data_file.exists():
        return None
    return pd.read_csv(data_file)

def save_data(
    df: pd.DataFrame,
    hash: str,
    data_folder: str,
) -> None:
    """Save data to file with a specific hash."""
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    df.to_csv(Path(data_folder) / f"{hash}.csv", index=False)