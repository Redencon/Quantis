"""Separate steps for Quantis run_quantis function.

## Steps
1. Load data
2. Modify data to fit universal format
3. Select score columns in initial dataframe
4. Impute missing values
5. Calculate Fold Change and p-value
5.1 Save intermediate results by hash value
6. Apply multiple testing correction
7. Calculate log2 of FC and -log10 of p-value
8. Calculate threshold for log2FC and -log10p
9. Apply thresholds and select DE proteins
10. Build plotly scatter plot (volcano plot)
11. Build data for DE proteins table

Some steps are optional for some tools.
Others are optional depending on set parameters.

Functions are separated to make it easier to construct pipelines without
repeating code and multiple confusing if-else statements."""

import pandas as pd
import numpy as np
from scipy.stats import ttest_ind, iqr
from statsmodels.stats.multitest import multipletests
import plotly.express as px
from plotly.graph_objects import Figure

from .knn_imputation import knn_impute
from .df_prep import load_from_lists

from typing import TypedDict, NamedTuple, Literal

class DEProtein(TypedDict):
    """DE protein data entry."""
    dbname: str
    FC: float
    logFDR: float

class ColorScheme(TypedDict):
    """Color scheme for DE proteins."""
    UP: str
    DOWN: str
    NOT: str

class Thresholds(NamedTuple):
    """Up and down FC and logFDR thresholds."""
    up_fc: float
    down_fc: float
    p_value: float

class TwoGroupDF(NamedTuple):
    """DataFrame with columns of two groups"""
    data: pd.DataFrame
    K_cols: list[str]
    A_cols: list[str]

class OneGroupDF(NamedTuple):
    """DataFrame with columns of two groups"""
    data: pd.DataFrame
    NSAF_cols: list[str]

class DFwThresholds(NamedTuple):
    """DataFrame with DE proteins and thresholds"""
    data: pd.DataFrame
    thresholds: Thresholds

MTC_method = Literal["bonferroni", "holm", "fdr_bh", "sh", "none"]
ThC_method = Literal["static", "semi-dynamic", "dynamic", "ms1"]
REG_types = Literal["UP", "DOWN", "BOTH"]


# Loading data and normalizing column names
def load_data_directms1quant(file: str):
    """Load data from DirectMS1Quant.
    
    Skips to step 10, as DirectMS1Quant already provides DE proteins
    """
    data = pd.read_csv(file, sep='\t')
    data['FC'] = data['log2FoldChange(S2/S1)']
    return data[['dbname', 'FC', 'p-value', 'FC_pass', 'BH_pass']]

def load_data_scavager(k_files: list[str], a_files: list[str]) -> TwoGroupDF:
    """Load data from Scavager.
    
    All steps are required. Multiple files are expected on input
    """
    data = load_from_lists(k_files, a_files)
    K_cols = [col for col in data.columns if col.startswith("NSAF_K")]
    A_cols = [col for col in data.columns if col.startswith("NSAF_A")]
    return TwoGroupDF(data, K_cols, A_cols)

def load_data_maxquant(file: str, K_cols: list[str], A_cols: list[str]) -> OneGroupDF:
    """Load data from MaxQuant.
    
    Same as Scavager, but with single file.
    """
    data = pd.read_csv(file, sep="\t")
    data = data[["Protein IDs"] + K_cols + A_cols].copy(deep=True)
    data.rename(columns={"Protein IDs": "dbname"}, inplace=True)
    data.replace(0, np.nan, inplace=True)
    NSAF_cols = K_cols + A_cols
    return OneGroupDF(data, NSAF_cols)

def load_data_diffacto(file: str) -> pd.DataFrame:
    """Load data from Diffacto.
    
    Similar to DirectMS1Quant, but without already calculated DE proteins.
    """
    data = pd.read_csv(file, sep='\t')
    data['dbname'] = data['Protein']
    data['FC'] = np.log2(data['S2']/data['S1'])
    data['p-value'] = data["P(PECA)"]
    return data[['dbname', 'FC', 'p-value']]

def impute_missing_values(ogdf: OneGroupDF, method: str) -> pd.DataFrame:
    """Impute missing values.
    
    This step is required for Scavager and MaxQuant.
    Imputation method should be specified.
    """
    if method == "Drop":
        data = ogdf.data.dropna(subset=ogdf.NSAF_cols).copy(deep=True)
    elif method == "Min":
        data = ogdf.data
        for col in ogdf.NSAF_cols:
            min_val = ogdf.data[col].min()
            data[col] = data[col].fillna(min_val)
    else:
        data_NSAF = ogdf.data.set_index('dbname')[ogdf.NSAF_cols]
        data_NSAF = knn_impute(data_NSAF)
        data = data_NSAF.reset_index().merge(ogdf.data[['dbname', 'description']], on='dbname', how='left')
    return data

def calculate_fold_change_p_value(tgdf: TwoGroupDF) -> pd.DataFrame:
    """Calculate Fold Change and p-value.
    
    This step is required for Scavager and MaxQuant.
    Groups should be specified.
    """
    data = tgdf.data
    data['FC'] = np.log2(data[tgdf.A_cols].mean(axis=1) / data[tgdf.K_cols].mean(axis=1))
    data['p-value'] =  data.apply(
        lambda row: ttest_ind(
            [row[column] for column in tgdf.K_cols],
            [row[column] for column in tgdf.A_cols]
        ).pvalue,  # type: ignore
        axis=1
        )
    return data


def apply_mtc_and_log(dft: DFwThresholds, mtc_method: MTC_method,) -> DFwThresholds:
    """Apply multiple testing correction. Log results.

    This step is required for Scavager and MaxQuant.
    """
    data = dft.data.copy()
    if mtc_method == "none":
        return dft
    if mtc_method == "bonferroni":
        ths = dft.thresholds
        new_thresholds = Thresholds(ths.up_fc, ths.down_fc, ths.p_value + np.log10(len(dft.data)))
        data["fdr"] = data["p-value"]
        data["logFDR"] = -np.log10(data["fdr"])
        return DFwThresholds(data, new_thresholds)
    data = dft.data.copy()
    data["fdr"] = multipletests(data["p-value"], method=mtc_method)[1]
    data["logFDR"] = -np.log10(data["fdr"])
    return DFwThresholds(data, dft.thresholds)

def calculate_thresholds(data: pd.DataFrame) -> Thresholds:
    """Calculate threshold for log2FC and -log10p.
    
    This step is required for Scavager and MaxQuant.
    """
    up_threshold = data['FC'].quantile(0.75) + iqr(data['FC']) * 1.5
    down_threshold = data['FC'].quantile(0.25) - iqr(data['FC']) * 1.5
    p_limit = data['logFDR'].quantile(0.75) + iqr(data['logFDR']) * 1.5
    return Thresholds(up_threshold, down_threshold, p_limit)

def replace_thresholds(old_thresholds: Thresholds, calc_threshold: Thresholds, method: ThC_method) -> Thresholds:
    if method == "static":
        return old_thresholds
    if method == "semi-dynamic":
        return Thresholds(old_thresholds.up_fc, old_thresholds.down_fc, calc_threshold.p_value)
    return calc_threshold

def calculate_thresholds_directms1quant(data: pd.DataFrame) -> Thresholds:
    """Calculate threshold for log2FC and -log10p.
    
    This step is required for DirectMS1Quant.
    """
    up_threshold = data[data["FC_pass"] & (data["FC"] > 0)]["FC"].min()
    down_threshold = data[data["FC_pass"] & (data["FC"] < 0)]["FC"].max()
    p_limit = data[data["BH_pass"]]["logFDR"].min()
    return Thresholds(up_threshold, down_threshold, p_limit)

def apply_thresholds(dwt: DFwThresholds, regulation: REG_types) -> tuple[DFwThresholds, pd.DataFrame]:
    """Apply thresholds and select DE proteins.
    
    This step is required for Scavager and MaxQuant.
    """
    def up_down_regulated(row, thresholds: Thresholds):
        if row['FC'] > thresholds.up_fc and row['logFDR'] > thresholds.p_value:
            return "UP"
        elif row['FC'] < thresholds.down_fc and row['logFDR'] > thresholds.p_value:
            return "DOWN"
        else:
            return "NOT"
    
    data = dwt.data.copy()
    data['regulation'] = data.apply(up_down_regulated, axis=1, thresholds=dwt.thresholds)
    dwt = DFwThresholds(data, dwt.thresholds)
    up_data = data[data['regulation'] == "UP"]
    down_data = data[data['regulation'] == "DOWN"]
    if regulation == "UP":
        return dwt, up_data
    if regulation == "DOWN":
        return dwt, down_data
    return dwt, pd.concat([up_data, down_data], ignore_index=True)


def build_volcano_plot(
    dwt: DFwThresholds,
    color_scheme: ColorScheme,
) -> Figure:
    """Build plotly scatter plot (volcano plot).
    
    This step is required for all paths.
    """
    fc_max = abs(dwt.data['FC']).max()
    vp = px.scatter(
        dwt.data, x='FC', y='logFDR', color='regulation',
        labels={'regulation': 'Regulation', 'FC': 'Fold Change', 'logFDR': '-log10(FDR)'},
        color_discrete_map=color_scheme, height=750, title='Volcano Plot', opacity=0.8,
        range_x=[-fc_max*1.1, fc_max*1.1], hover_data={'dbname': True}
    )
    vp.update_layout(
        title_font_family="Montserrat",
        font_family="Montserrat"
    )
    vp.add_hline(y=dwt.thresholds.p_value, line_dash="dash", line_color="gray")
    vp.add_vline(x=dwt.thresholds.up_fc, line_dash="dash", line_color="gray")
    vp.add_vline(x=dwt.thresholds.down_fc, line_dash="dash", line_color="gray")
    return vp


"""
Diffacto run section

Expected input files: PSM tables from Scavager (K_files, A_files)

(Input File Format: Scavager(diffacto quantitation))
"""
from pathlib import Path
import subprocess


class DiffactoError(subprocess.CalledProcessError): pass


SERVICE_PATH = Path(__file__).parent / "service"

def load_data_for_diffacto(k_files: list[str], a_files: list[str]):
    """Prepare input data for diffacto run."""
    sample_dict = {"K": [], "A": []}
    df0 = pd.DataFrame(columns=["peptide", "protein"])
    i = 1
    intensity_column = None
    if intensity_column is None:
        raise NotImplementedError("Please specify intensity column")
    for group, label in zip([k_files, a_files], ["K", "A"]):
        for file in group:
            df = pd.read_csv(file, sep="\t")[['peptide', 'protein', intensity_column]]
            df0 = pd.merge(df0, df, on=["peptide", "protein"], how="outer")
            sample_dict[label].append(f"rep{i}")
            i += 1
    
    df0.fillna("", inplace=True)
    di = SERVICE_PATH / "diffacto_input.tsv"
    dis = SERVICE_PATH / "diffacto_input_samples.txt"
    df0.to_csv(di, sep=",", index=False)
    with open(dis, "w") as f:
        f.write("\n".join([[f"K\t{rep}" for rep in sample_dict["K"]]]))
        f.write("\n".join([[f"A\t{rep}" for rep in sample_dict["K"]]]))
    return di, dis

def run_diffacto(input: str, samples: str, path_to_diffacto: str):
    result = SERVICE_PATH / "diffacto_output.txt"
    args = [path_to_diffacto, "-i", input, "-s", samples, "-out", result]
    spc = subprocess.run(args, capture_output=True, check=True)
    try:
       spc.check_returncode()
    except subprocess.CalledProcessError as e:
        raise DiffactoError(e.stderr.decode()) 
    return result

# After diffacto finished it's run, we can shove the results into already
# existing piplene of diffacto result files reading and processing

# o = run_diffacto(di, dis, "diffacto")
# data = load_data_diffacto(o)
# and continue with the pipeline
  