from . import log_setup
from dash import Dash, dcc, callback, Input, Output, State, html, no_update, dash_table, ctx
import dash_uploader as du
from dash_daq.ColorPicker import ColorPicker
from plotly.express import scatter
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import ttest_ind, iqr
from statsmodels.stats.multitest import multipletests
import atexit

import webview

from .knn_imputation import knn_impute
from .ncbi_species_parser import fetch_species_name
from .cash_or_new import hash_parameters, check_existing_data, save_data
from .df_prep import load_from_lists, load_from_lists_mq
from .string_request import get_string_svg
from .open_tsv_files_dialog import open_tsv_files_dialog, save_csv_file_dialog


FILES_PATH = Path(__file__).parent / "user_files"
CACHE_PATH = Path(__file__).parent / "data_cache"
ASSETS_PATH = Path(__file__).parent / "assets"

def resource_path(relative_path):
    """get absolute path to resource"""
    import sys
    import os
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = Path(__file__).parent
    return os.path.join(base_path, relative_path)



# app = Dash("Quantis", external_stylesheets=["style.css"])
app = Dash("Quantis", title="Quantis", assets_folder=str(resource_path("assets")))
du.configure_upload(app, FILES_PATH, use_upload_id=False)


app.layout = html.Div([
    html.Div(
        html.Header("Quantis"),
        className="header-fullwidth"
    ),
    html.Div([

        html.H2("Input"),
        html.Div([
            html.P("Input file format: ", style={'marginRight': '0.5em'}),
            dcc.Dropdown(
                id="input_format", options=["Scavager", "MaxQuant", "DirectMS1Quant"], value="Scavager",
                clearable=False, style={'width': '13em'}
            ),
        ], style={'display': 'flex', 'flex-direction': 'row', 'width': '100%'}),
        html.Div([
            html.Button("Upload score file", id='single_input_btn', className="upload_button"),
            dcc.Input(id="single_file_path", value="", placeholder="No file selected", disabled=True, className="path_input"),
        ], style={"diplay": "hidden"}, id="single_input_div"),
        html.Div([
            html.Div([
                html.Div([
                    dcc.Input(id="control_name", type="text", placeholder="Control", className="group-title"),
                    # du.Upload(id="control_input", filetypes=['tsv'], text="Upload Control", max_files=10),
                    html.Button("Upload control files", id="control_btn_input", className="upload_button"),
                    dash_table.DataTable(
                        id="control_files_table", columns=[{"id": "path", "name": "File Path"}],
                        editable=False, row_selectable="multi", cell_selectable=False,
                        style_cell={
                            'overflow': 'hidden', 'textOverflow': 'ellipsis',
                            'maxWidth': 0, 'textAlign': 'left', 'direction': 'rtl'}),
                    dcc.Input(id="lastfiles_K", type="hidden", value=""),
                    html.Div([
                        html.Button("Remove selected", id="rm_K_sel_btn", className="rm_button"),
                        html.Button("Remove all", id="rm_K_all_btn", className="rm_button"),
                    ], style={'display': 'flex', 'flex-direction': 'row', 'justify-content': 'space-between'}),
                ], style={"padding": 10, 'flex': 1}),
                html.Div([
                    dcc.Input(id="test_name", type="text", placeholder="Test", className="group-title"),
                    html.Button("Upload test files", id="test_btn_input", className="upload_button"),
                    # du.Upload(id="test_input", filetypes=['tsv'], text="Upload Test", max_files=10),
                    dash_table.DataTable(
                        id="test_files_table", columns=[{"id": "path", "name": "File Path"}],
                        editable=False, row_selectable="multi", cell_selectable=False,
                        style_cell={
                            'overflow': 'hidden', 'textOverflow': 'ellipsis',
                            'maxWidth': 0, 'textAlign': 'left', 'direction': 'rtl'}),
                    dcc.Input(id="lastfiles_A", type="hidden", value=""),
                    html.Div([
                        html.Button("Remove selected", id="rm_A_sel_btn", className="rm_button"),
                        html.Button("Remove all", id="rm_A_all_btn", className="rm_button"),
                    ], style={'display': 'flex', 'flex-direction': 'row', 'justify-content': 'space-between'}),
                ], style={"padding": 10, 'flex': 1}),
            ], style={'display': 'flex', 'flex-direction': 'row'}),
            dcc.Download(id="download_sample"),
            html.Button("Generate Sample File", id="sample_gen_btn", className="download_button"),
            html.P("Or use a sample file:"),
            du.Upload(id="sample_input", filetypes=['csv'], text="Upload Sample File", max_files=1),
            html.Details([
                html.Summary("What is sample file?", style={'font-size': '16pt'}),
                html.P(
                    "Sample file is a csv file, containing informtion about input files. "
                    + "It is expected to have two columns: Path with absolute paths to files "
                    + "and Sample, containing letters K and A for control and test files respectfully."
                )
            ]),
        ], style={"diplay": "grid"}, id="multi_input_div"),
        html.Br(),

        # A collapsible div with quantification parameters, collapsed by default
        html.Details([
            html.Summary("Quantification Parameters"),
            html.Table([
                # First row
                html.Tr([
                    html.Td("Imputation", style={"width": "32%"}),
                    html.Td("Regulation", style={"width": "32%"}),
                    html.Td("Threshold calculation", style={"width": "32%"}),
                    
                ]),
                html.Tr([
                    html.Td(dcc.Dropdown(id="imputation", options=["Drop", "Min", "kNN"], value="Min", clearable=False)),
                    html.Td(dcc.Dropdown(id="regulation", options=["UP", "DOWN", "BOTH"], value="BOTH", clearable=False)),
                    html.Td(dcc.Dropdown(id="threshold_calculation", options=[
                        {"label": "static", "value": "static"},
                        {"label": "semi-dynamic", "value": "semi-dynamic"},
                        {"label": "dynamic", "value": "dynamic"},
                        {"label": "MS1", "value": "ms1", "disabled": True}
                    ], value="static", clearable=False)),
                ]),

                # Second row
                html.Tr([
                    html.Td("Multiple-testing correction", style={"width": "32%"}),
                    html.Td("Species", colSpan=2, style={"width": "64%"}),
                ]),
                html.Tr([
                    html.Td(dcc.Dropdown(id="correction", options=[
                        {"label": "Bonferroni", "value": "bonferroni"},
                        {"label": "Holm", "value": "holm"},
                        {"label": "Benjamini-Hochberg", "value": "fdr_bh"},
                        {"label": "Simes-Hochberg", "value": "sh"}
                    ], value="fdr_bh", clearable=False)),
                    html.Td(dcc.Dropdown(id="species", options=[
                            {"label": "H. sapiens", "value": 9606},
                            {"label": "M. musculus", "value": 10090},
                            {"label": "S. cerevisiae", "value": 4932},
                            {"label": "Custom...", "value": -1}
                    ], value=9606, clearable=False)),
                    html.Td([
                        dcc.Input(id="custom_species", type="number", placeholder="NCBI Taxonomy ID", disabled=True, value=9606),
                        html.P(id="species_name", style={"font-style": "italic"}, children="")
                    ]),
                ])
            ], style={"padding": 10, 'width': '100%'}),
        ], open=True),

        # Fold change and p-value threshold value sliders with input fields
        # Not collapsible
        html.Div([
            html.H3("Fold Change Threshold"),
            html.Div([
                dcc.Input(id="fold_change_input", type="number", value=1, style={"width": "15%"}),
                html.Div(dcc.Slider(
                    id="fold_change_slider", min=0.5, max=3, step=0.1, value=1, marks={0.5*i: f"{0.5*i}" for i in range(1,7)}
                ), style={"width": "80%"}),
            ], style={"padding": 10, 'display': 'flex', 'flex-direction': 'row'}),
            html.H3("P-value Threshold"),
            html.Div([
                dcc.Input(id="pvalue_input", type="number", value=0.01, style={"width": "15%"}),
                html.Div(dcc.Slider(
                    id="pvalue_slider", min=-5, max=-1, step=0.1,
                    value=-2, marks={i: f"{10**i}" for i in range(-5, 0)}
                ), style={"width": "80%"}),
            ], style={"padding": 10, 'display': 'flex', 'flex-direction': 'row'}),
        ]),
    
        # A collapsible div with style parameters
        html.Details([
            html.Summary("Style Parameters (WIP)"),
            html.Div([
                ColorPicker(id="up_color", label="UP points", value={'hex': "#890c0c"}),
                ColorPicker(id="down_color", label="DOWN points", value={'hex': "#42640a"}),
                ColorPicker(id="not_color", label="Background points", value={'hex': "#129dfc"}),
            ], style={"padding": 10, "display": "flex", "flex-direction": "row"})
        ]),

        # Button to start the analysis
        html.Button(
            "Start Analysis", id="start_button", className="start_button",
            style={'margin-left': 'auto', 'margin-right': 'auto'}
        ),
        html.Hr(),
    ], className="container"),
    html.Div([
        # ====== Results ======
        dcc.Loading(dcc.Graph(id="volcano_plot"), type="graph"),
        dcc.Loading(html.Img(
            id="string_svg",
            style={"display": "block", "margin-left": "auto", "margin-right": "auto", 'max-width': '100%'}
        ), type="circle"),
        html.H3("Differentially Expressed Proteins"),
        html.Button("Save DE protens", id="save_proteins_button", disabled=True),
        dcc.Download(id="download_proteins"),
        dash_table.DataTable(
            id="result_proteins_table",
            columns=[
                {"name": "Protein", "id": "dbname"},
                {"name": "Fold Change", "id": "FC"},
                {"name": "p-value", "id": "logFDR"},
            ],
            style_cell_conditional=[{
                'if': {'column_id': 'dbname'},
                'textAlign': 'left'
            }]
        ),
    ])
])

window = webview.create_window(app.title, app.server, width=1200, height=800)  # type: ignore

# ======== Callbacks ========

# Show proper div for currently chosen input format
@callback(
    Output("single_input_div", "style"),
    Output("multi_input_div", "style"),
    Input("input_format", "value")
)
def hide_show_divs(value):
    if value == "Scavager":
        return {"display": "none"}, {"display": "grid"}
    else:
        return {"display": "grid"}, {"display": "none"}


# Disable threshold type and sliders for DirectMS1Quant
@callback(
    Output("threshold_calculation", "disabled"),
    Output("threshold_calculation", "value"),
    Output("imputation", "disabled"),
    Input("input_format", "value")
)
def disable_threshold(value):
    if value == "DirectMS1Quant":
        return True, "ms1", True
    else:
        return False, "static", False


# Add files to tables
@callback(
    Output("control_files_table", "data", allow_duplicate=True),
    Input("lastfiles_K", "value"),
    State("control_files_table", "data"),
    prevent_initial_call=True
)
def append_control_files(lastfiles: str, data: list[dict] | None):
    if data is None: # Prevents error when data is None
        data = []
    lfl = lastfiles.split(";")
    if not lfl:
        return no_update
    
    all_paths = set(row["path"] for row in data)

    for file in lfl:
        if file not in all_paths:
            data.append({"path": file})
    
    return data

@callback(
    Output("test_files_table", "data", allow_duplicate=True),
    Input("lastfiles_A", "value"),
    State("test_files_table", "data"),
    prevent_initial_call=True
)
def append_test_files(lastfiles: str, data: list[dict] | None):
    if data is None: # Prevents error when data is None
        data = []
    lfl = lastfiles.split(";")
    if not lfl:
        return no_update
    
    all_paths = set(row["path"] for row in data)

    for file in lfl:
        if file not in all_paths:
            data.append({"path": file})
    
    return data

# Remove files from tables

@callback(
    Output("control_files_table", "data", allow_duplicate=True),
    Input("rm_K_sel_btn", "n_clicks"),
    State("control_files_table", "selected_rows"),
    State("control_files_table", "data"),
    prevent_initial_call=True
)
def rm_sel_K(_, selected_rows: list[int], data: list[dict]):
    # for i, row in enumerate(data):
    #     if i in selected_rows:
    #         FILES_PATH.joinpath(row["path"]).unlink()
    return [row for i, row in enumerate(data) if i not in selected_rows]

@callback(
    Output("test_files_table", "data", allow_duplicate=True),
    Input("rm_A_sel_btn", "n_clicks"),
    State("test_files_table", "selected_rows"),
    State("test_files_table", "data"),
    prevent_initial_call=True
)
def rm_sel_A(_, selected_rows: list[int], data: list[dict]):
    # for i, row in enumerate(data):
    #     if i in selected_rows:
    #         FILES_PATH.joinpath(row["path"]).unlink()
    return [row for i, row in enumerate(data) if i not in selected_rows]

@callback(
    Output("control_files_table", "data", allow_duplicate=True),
    Input("rm_K_all_btn", "n_clicks"),
    State("control_files_table", "data"),
    prevent_initial_call=True
)
def rm_all_K(_, data):
    # for file in data:
    #     FILES_PATH.joinpath(file["path"]).unlink()
    return []

@callback(
    Output("test_files_table", "data", allow_duplicate=True),
    Input("rm_A_all_btn", "n_clicks"),
    State("test_files_table", "data"),
    prevent_initial_call=True
)
def rm_all_A(_, data):
    # for file in data:
    #     FILES_PATH.joinpath(file["path"]).unlink()
    return []

# Generate sample file from table data
@callback(
    Output("download_sample", "data"),
    Input("sample_gen_btn", "n_clicks"),
    State("control_files_table", "data"),
    State("test_files_table", "data"),
    prevent_initial_call=True
)
def generate_sample_file(_, k_data, a_data):
    if not k_data or not a_data:
        return no_update
    k_files = pd.DataFrame(k_data)
    a_files = pd.DataFrame(a_data)
    k_files["Sample"] = "K"
    a_files["Sample"] = "A"
    sample = pd.concat([k_files, a_files], ignore_index=True)
    sample = sample.rename(columns={"path": "Path"})
    path = save_csv_file_dialog(window)
    if path:
        sample.to_csv(str(path), index=False)
    return None


# Select files with sample file
@du.callback(
    [Output("control_files_table", "data", allow_duplicate=True),
    Output("test_files_table", "data", allow_duplicate=True)],
    id="sample_input"
)
def load_sample_file(status: du.UploadStatus):
    if not status.uploaded_files:
        return no_update, no_update
    
    # Load the sample file
    sdf = pd.read_csv(FILES_PATH / status.uploaded_files[0].name)
    k_files = [{"path": f} for f in sdf[sdf["Sample"] == "K"]["Path"].tolist()]
    a_files = [{"path": f} for f in sdf[sdf["Sample"] == "A"]["Path"].tolist()]
    return k_files, a_files

# Enable/disable custom species input
@callback(
    Output("custom_species", "disabled"),
    Output("custom_species", "value"),
    Input("species", "value")
)
def disable_custom_species(value):
    if value == -1:
        return False, no_update
    else:
        return True, ""


# Display custom species name
@callback(
    Output("species_name", "children"),
    Input("custom_species", "value"),
    prevent_initial_call=True
)
def custom_species_name(taxid):
    if taxid == "":
        return ""
    try:
        return fetch_species_name(taxid)
    except ValueError:
        return "Species not found"


# Sync fold change slider and input
@callback(
    Output("fold_change_input", "value"),
    Output("fold_change_slider", "value"),
    Input("fold_change_input", "value"),
    Input("fold_change_slider", "value"),
)
def fc_sync(input_val, slider_val):
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "fold_change_input":
        return input_val, input_val
    else:
        return slider_val, slider_val

# Sync p-value slider and input
@callback(
    Output("pvalue_input", "value"),
    Output("pvalue_slider", "value"),
    Input("pvalue_input", "value"),
    Input("pvalue_slider", "value"),
)
def pvalue_sync(input_val, slider_val):
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "pvalue_input":
        return input_val, round(np.log10(input_val), 2)
    else:
        return 10**slider_val, slider_val


# Block sliders on dynamic threshold calculation
@callback(
    Output("fold_change_slider", "disabled"),
    Output("pvalue_slider", "disabled"),
    Output("fold_change_input", "disabled"),
    Output("pvalue_input", "disabled"),
    Input("threshold_calculation", "value"),
)
def disable_sliders(value):
    if value == "dynamic" or value == "ms1":
        return True, True, True, True
    elif value == "semi-dynamic":
        return False, True, False, True
    else:
        return False, False, False, False


NULL_PLOT = {
    "layout": {
        "xaxis": {
            "visible": False
        },
        "yaxis": {
            "visible": False
        },
        "annotations": [
            {
                "text": "No data to display",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {
                    "size": 28
                }
            }
        ]
    }
}

# Start analysis
@callback(
    Output("volcano_plot", "figure"),
    Output("result_proteins_table", "data"),
    Output("save_proteins_button", "disabled"),
    Input("fold_change_input", "value"),
    Input("pvalue_input", "value"),
    Input("start_button", "n_clicks"),
    Input("regulation", "value"),
    Input("correction", "value"),
    Input("threshold_calculation", "value"),
    State("control_files_table", "data"),
    State("test_files_table", "data"),
    State("single_file_path", "value"),
    State("imputation", "value"),
    State("species", "value"),
    State("custom_species", "value"),
    State("up_color", "value"),
    State("down_color", "value"),
    State("not_color", "value"),
    State("input_format", "value"),
    prevent_initial_call=True,
)
def run_quantis(
    fc_threshold, pvalue_threshold, _,
    regulation, correction,
    threshold_calculation,
    control_files, test_files, single_file,
    imputation, species, custom_species,
    up_color, down_color, not_color,
    input_format
):
    # Select species or custom species
    if species == -1:
        species = custom_species

    if input_format == "DirectMS1Quant":
        # Check if single file is provided
        if not single_file:
            return NULL_PLOT, no_update, no_update
        
        # Separate pathway for DirectMS1Quant
        data = pd.read_csv(single_file, sep='\t')
        data['FC'] = data['log2FoldChange(S2/S1)']
        data['fdr'] = multipletests(data['p-value'], method=correction)[1]
        data['logFDR'] = -np.log10(data['fdr'])
        up_threshold = data[data["FC_pass"] & (data["FC"] > 0)]["FC"].min()
        down_threshold = data[data["FC_pass"] & (data["FC"] < 0)]["FC"].max()
        p_limit = data[data["BH_pass"]]["logFDR"].min()
    else:
        # Check if files are provided
        if not control_files or not test_files:
            return NULL_PLOT, no_update, no_update

        # Turn files into lists
        cfl = [FILES_PATH / f["path"] for f in control_files]
        tfl = [FILES_PATH / f["path"] for f in test_files]
        # Hash parameters
        _hash = hash_parameters(cfl, tfl, imputation, input_format)

        # Check if data is already present
        data = check_existing_data(_hash, str(CACHE_PATH))

        if data is None:
            # Fetch new data
            if input_format == "Scavager":
                data = load_from_lists(cfl, tfl)
            elif input_format == "MaxQuant":
                data = load_from_lists_mq(cfl, tfl)
            else:
                raise ValueError("Unsupported input file format: {}".format(input_format))
            NSAF_cols = [col for col in data.columns if "NSAF" in col]
            if imputation == "Drop":
                data = data.dropna()
            elif imputation == "Min":
                for col in NSAF_cols:
                    min_val = data[col].min()
                    data[col] = data[col].fillna(min_val)
            else:
                data_NSAF = data.set_index('dbname')[NSAF_cols]
                data_NSAF = knn_impute(data_NSAF)
                data = data_NSAF.reset_index().merge(data[['dbname', 'description']], on='dbname', how='left')
        
            # Calculate fold change and p-values
            K_cols = [col for col in data.columns if col.startswith("NSAF_K")]
            A_cols = [col for col in data.columns if col.startswith("NSAF_A")]
            data['FC'] = np.log2(data[A_cols].mean(axis=1) / data[K_cols].mean(axis=1))
            data['p-value'] =  data.apply(
                lambda row: ttest_ind(
                    [row[column] for column in K_cols],
                    [row[column] for column in A_cols]
                ).pvalue,  # type: ignore
                axis=1
            )
            # data['logp'] = -np.log10(data['p-value'])
            # data['logFC'] = np.log2(data['FC'])
        
            # Save data
            save_data(data, _hash, str(CACHE_PATH))

        # Apply multiple testing correction
        data['fdr'] = multipletests(data['p-value'], method=correction)[1]
        data['logFDR'] = -np.log10(data['fdr'])
        
        # Calculate thresholds
        if threshold_calculation == "static":
            up_threshold = fc_threshold
            down_threshold = -fc_threshold
            p_limit = -np.log10(pvalue_threshold)
        elif threshold_calculation == "semi-dynamic":
            up_threshold = fc_threshold
            down_threshold = -fc_threshold
            p_limit = data['logFDR'].quantile(0.75) + iqr(data['logFDR']) * 1.5
        else:
            up_threshold = data['FC'].quantile(0.75) + iqr(data['FC']) * 1.5
            down_threshold = data['FC'].quantile(0.25) - iqr(data['FC']) * 1.5
            p_limit = data['logFDR'].quantile(0.75) + iqr(data['logFDR']) * 1.5
        
        assert p_limit > 0, "p_limit is not positive: {:.4f} | {:.4f} | {:.4f}".format(p_limit, data['logFDR'].quantile(0.75), iqr(data['logFDR']) * 1.5)

    # Filter data
    def up_down_regulated(row):
        if row['FC'] > up_threshold and row['logFDR'] > p_limit:
            return "UP"
        elif row['FC'] < down_threshold and row['logFDR'] > p_limit:
            return "DOWN"
        else:
            return "NOT"

    data['regulation'] = data.apply(up_down_regulated, axis=1)

    if regulation == "UP" or regulation == "BOTH":
        up_data = data[data['regulation'] == "UP"]
    else:
        up_data = pd.DataFrame(columns=data.columns)
    
    if regulation == "DOWN" or regulation == "BOTH":
        down_data = data[data['regulation'] == "DOWN"]
    else:
        down_data = pd.DataFrame(columns=data.columns)

    merged_data = pd.concat([up_data, down_data], ignore_index=True)

    # Create volcano plot
    colors = {
        'UP': up_color['hex'], 'DOWN': down_color['hex'], 'NOT': not_color['hex']
    }

    fc_max = abs(data['FC']).max()

    vp = scatter(
        data, x='FC', y='logFDR', color='regulation',
        labels={'regulation': 'Regulation', 'FC': 'Fold Change', 'logFDR': '-log10(FDR)'},
        color_discrete_map=colors, height=750, title='Volcano Plot', opacity=0.8,
        range_x=[-fc_max*1.1, fc_max*1.1]
    )
    vp.add_hline(y=p_limit, line_dash="dash", line_color="gray")
    vp.add_vline(x=up_threshold, line_dash="dash", line_color="gray")
    vp.add_vline(x=down_threshold, line_dash="dash", line_color="gray")
    
    # vp = VolcanoPlot(
    #     dataframe=data, effect_size='FC', p='fdr',
    #     snp='dbname', gene='description', xlabel='Fold Change',
    #     ylabel='-log10(FDR)', title='Volcano Plot',
    #     effect_size_line=[down_threshold, up_threshold],
    #     genomewideline_value=p_limit, height=750
    # )

    # Results table
    results = merged_data[["dbname", "FC", "logFDR"]].to_dict("records")

    return vp, results, False


# Show StringDB network
@callback(
    Output("string_svg", "src"),
    Input("result_proteins_table", "data"),
    prevent_initial_call=True
)
def show_string_network(data):
    if not data:
        return no_update

    proteins = [row["dbname"].split("|")[1] for row in data]
    return get_string_svg(proteins)


# Save DE proteins
@callback(
    Output("download_proteins", "data"),
    Input("save_proteins_button", "n_clicks"),
    State("result_proteins_table", "data"),
    prevent_initial_call=True
)
def save_proteins(_, data):
    df = pd.DataFrame(data)
    path = save_csv_file_dialog(window)
    if path:
        df.to_csv(str(path), index=False)
    return None

@callback(
    Output("lastfiles_K", "value"),
    Input("control_btn_input", "n_clicks"),
    prevent_initial_call=True
)
def write_control_files(_):
    return ";".join(open_tsv_files_dialog(window) or [])

@callback(
    Output("lastfiles_A", "value"),
    Input("test_btn_input", "n_clicks"),
    prevent_initial_call=True
)
def write_test_files(_):
    return ";".join(open_tsv_files_dialog(window) or [])

@callback(
    Output("single_file_path", "value"),
    Input("single_input_btn", "n_clicks"),
    prevent_initial_call=True
)
def write_single_file(_):
    path = open_tsv_files_dialog(window, False)
    if path:
        return path[0]
    return ""


# On scipt exit remove uploaded files
def remove_files():
    for file in FILES_PATH.iterdir():
        file.unlink()
    for file in CACHE_PATH.iterdir():
        file.unlink()

def create_user_files_dirs():
    if not FILES_PATH.exists():
        FILES_PATH.mkdir()
    if not CACHE_PATH.exists():
        CACHE_PATH.mkdir()

atexit.register(remove_files)

def start_webview():
    create_user_files_dirs()
    webview.start()


if __name__ == "__main__":
    # app.run_server(debug=False)
    create_user_files_dirs()
    start_webview()