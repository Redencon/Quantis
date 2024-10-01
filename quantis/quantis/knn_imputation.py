"""knn imputation for nsaf columns

Copyright 2024 Daniil Pomogaev
SPDX-License-Identifier: Apache-2.0
"""

from sklearn.impute import KNNImputer
import pandas as pd


def knn_impute(df: pd.DataFrame, n_neighbors: int = 5) -> pd.DataFrame:
    """Impute missing values using K-Nearest Neighbors algorithm."""
    imputer = KNNImputer(n_neighbors=n_neighbors, weights='uniform', metric='nan_euclidean')
    NSAF_cols = [col for col in df.columns if col.startswith('NSAF')]
    df['% NaN'] = df[NSAF_cols].isna().sum(axis=1) / len(NSAF_cols)
    df0 = df[df['% NaN'] == 0].copy(deep=True)[NSAF_cols]
    dfknn = df[df['% NaN'] != 0].copy(deep=True)[NSAF_cols]
    imputer.fit(df0)
    dfknn = pd.DataFrame(imputer.transform(dfknn), columns=dfknn.columns, index=dfknn.index)
    return pd.concat([df0, dfknn]).reset_index()