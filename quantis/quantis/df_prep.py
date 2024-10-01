"""Functions responsible for loading or prepearing data for analysis.

Copyright 2024 Daniil Pomogaev
SPDX-License-Identifier: Apache-2.0
"""


import os
import pandas as pd


def load_from_sample_file(s_file_path: str) -> pd.DataFrame:
    """Load sample data wih specifications from sample file.
    
    Returns single pd.DataFrame with columns:
    - 'dbname' - protein database name
    - 'description' - protein description
    - 'NSAF_x_y' - NSAF value for sample x, run y (multiple columns)

    Expected samples: 'K' for control samples, 'A' for experimental samples.
    
    NSAF stands for Normalized Spectral Abundance Factor.
    """
    if not os.path.exists(s_file_path):
        raise FileNotFoundError(f"File {s_file_path} not found.")
    
    samples = pd.read_csv(s_file_path, sep='\t')  # Sample file has columns: Sample, Run, Path

    df = pd.DataFrame(columns=['dbname', 'description'])

    for file in samples.itertuples():
        sample = pd.read_csv(str(file.Path), sep='\t')
        sample = sample[['dbname', 'description', 'NSAF']]
        sample.rename(columns={'NSAF': f'NSAF_{file.Sample}_{file.Run}'}, inplace=True)
        df = df.merge(sample, on=['dbname', 'description'], how='outer')

    return df


def load_from_lists(k_files: list[str], a_files: list[str]) -> pd.DataFrame:
    """Load sample data from lists of files.

    Returns single pd.DataFrame with columns:
    - 'dbname' - protein database name
    - 'description' - protein description
    - 'NSAF_x_y' - NSAF value for sample x, run y (multiple columns)
    """
    df = pd.DataFrame(columns=['dbname', 'description'])

    # Iterate over two lists: k with control samples and a with experimental samples
    for s, flist in zip(['K', 'A'], [k_files, a_files]): # s - sample type, flist - list of files
        for i, file in enumerate(flist, start=1): # i - run number, file - file path
            sample = pd.read_csv(file, sep='\t')
            sample = sample[['dbname', 'description', 'NSAF']]
            sample.rename(columns={'NSAF': f'NSAF_{s}_{i}'}, inplace=True)
            df = df.merge(sample, on=['dbname', 'description'], how='outer')

    return df


def load_from_lists_mq(k_files: list[str], a_files: list[str]) -> pd.DataFrame:
    """Load data from lists of file paths. Adjust MaxQuant format for further usage.
    
    Just as well, returns single pd.DataFrame with columns:
    - 'dbname' - protein database name
    - 'description' - protein description
    - 'NSAF_x_y' - normalised iBAQ value for sample x run y (multiple columns)

    Name discrepancy is added for cross-compatibiblity.
    """
    df = pd.DataFrame(columns=['dbname', 'descripton'])

    for s, flist in zip(['K', 'A'], [k_files, a_files]):
        for i, file in enumerate(flist, start=1):
            sample = pd.read_csv(file, sep='\t')
            sample['dbname'] = sample['Protein IDs'].apply(lambda l: (l[0] if isinstance(l, list) else l))
            sample['description'] = sample['Gene names'].apply(lambda l: (l[0] if isinstance(l, list) else l))
            sample[f'NSAF_{s}_{i}'] = sample['iBAQ']/sample['iBAQ'].sum()
            df = df.merge(sample, on=['dbname', 'description'], how='outer')

    return df