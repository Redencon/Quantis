"""Fancy Dash output for a collection of scavager output files"""


import dash_bio
from dash import Dash, dcc, callback, Input, Output, State, html, no_update, dash_table
import pandas as pd
import scipy.stats as sps
import numpy as np
import os
import base64
import requests as rqt

DIRECTORY = "fragger_close"

file_data = pd.read_csv("file_data.csv")
BETTER_DATA_TEMPLATE = "/home/redencon/quant_study/better_data/{}_proteins.tsv"

def get_data(experiment: str, lognsaf: bool = False):
    """Return composite dataframe with NSAF values for every protein in a given experiment"""
    files = file_data[file_data["Sample"] == experiment]
    df = pd.DataFrame(columns=["dbname", "NSAF"])
    columns = []
    for file in files.itertuples():
        data = pd.read_csv(BETTER_DATA_TEMPLATE.format(file.File_Name), sep="\t")
        sample = file.Biorep[0]
        run = file.Biorep[1]
        rrun = file.Techrep[1]
        df = pd.merge(df, data[['dbname', 'NSAF']], "outer", "dbname", suffixes=[None, "_{}_{}{}".format(sample, run, rrun)])
        columns.append("NSAF_{}_{}{}".format(sample, run, rrun))
        if lognsaf:
            df["NSAF_{}_{}{}".format(sample, run, rrun)] = df["NSAF_{}_{}{}".format(sample, run, rrun)].apply(np.log2)
    del run, sample, data, rrun
    df.drop("NSAF", axis=1, inplace=True)

    if not os.path.exists(os.path.join("background", "{}.txt".format(experiment))):
        with open(os.path.join("background", "{}.txt".format(experiment)), "w") as f:
            f.write("\n".join(df["dbname"].apply(lambda s: s.split("|")[1]).to_list()))
    df['wasna'] = df[columns].isna().apply(lambda row: any(row), axis=1)
    
    # for col in columns:
    #     mean = df[df["wasna"]][col].mean()
    #     std = df[df["wasna"]][col].std()
    #     df[col] = (df[col] - mean)/std
    df.fillna(
        {column: df[column].min() for column in df.columns},
        inplace=True
    )
    return normalize_nsaf(df)

def normalize_nsaf(df: pd.DataFrame):
    """Normalize NSAF columns by adjusting standard deviation and mean value"""
    df = df.copy()
    columns = [col for col in df.columns if "NSAF" in col]
    for column in columns:
        mean = df[column].mean()
        std = df[column].std()
        df[column] = df[column].apply(lambda x: (x - mean)/std)
    return df

def get_means(df: pd.DataFrame):
    """Return mean value of NSAF for K and a samples for each protein in df"""
    df_means = df[["dbname"]].copy()
    columns = [col for col in df.columns if "NSAF" in col]
    samples = ["K", "a"]
    for sample in samples:
        b = 0
        for column in columns:
            if "_{}_".format(sample) not in column:
                continue
            b += df[column]
        df_means["NSAF_{}".format(sample)] = b/4
    del b, sample
    return df_means

def fcp(df: pd.DataFrame):
    """Calculate Fold Change and ttest p-value for NSAF values for each protein in K and a samples"""
    df_means = get_means(df)
    dff = df[["dbname"]].copy()
    columns = df.columns
    # Calculate FoldChange and ttest p-value
    dff['FC'] = df_means['NSAF_a'] - df_means['NSAF_K']
    dff['pvalue'] = df.apply(
        lambda row: sps.ttest_ind(
            [row[column] for column in columns if "NSAF_K_" in column],
            [row[column] for column in columns if "NSAF_a_" in column]
        ).pvalue,
        axis=1
    )
    dff["wasna"] = df["wasna"]
    dff['logp'] = -np.log10(dff['pvalue'])
    return dff

def get_string_svg(proteins):
    """Get html-injectable svg of a String plot for given set of proteins
    
    Based on `show_string_picture` function from
    https://github.com/kazakova/Metrics/blob/main/QRePS/stattest_metrics.py
    """
    if not proteins:
        return ""
    string_api_url = "https://string-db.org/api/"
    output_format = "svg"
    method = "network"
    request_url = string_api_url + output_format + "/" + method
    params = {
    "identifiers" : "%0d".join(proteins), # your protein
    "species": "9606"
    }
    try:
        res = rqt.post(request_url, params)
    except rqt.HTTPError as exception:
        return ""
    return 'data:image/svg+xml;base64,{}'.format(base64.b64encode(res.content).decode())

# Prepare data for Volcano-plot
# --- DATA ASSEMBLY : OVER ---

# Plotly (Dash) app

app = Dash("Quantitve Analisys", external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

app.layout = html.Div([
    html.Header([
        html.H1(children="Quantitive analisys", style={"textAlign": "center"}),
        html.H5(children="Interactive app by Redencon (D. Pomogaev)", style={"textAlign": "center"}),
    ]),
    html.P("Enter experiment number"),
    dcc.Dropdown(file_data["Sample"].drop_duplicates().to_list(), file_data["Sample"].to_list()[0], id="experiment"),
    html.Hr(),
    html.P(id="file_err", style={"color": "red"}),
    html.Br(),
    html.Div([
        html.P("p-value"),
        dcc.Slider(
            min=0,
            max=5,
            step=1,
            marks={i: str(v) for i, v in enumerate([0.001, 0.005, 0.01, 0.05, 0.1, 0.5])},
            value=3,
            id="p-value-slider"
        )
    ]),
    html.Br(),
    html.Div([
        html.P("FC"),
        dcc.Slider(
            min=0.5,
            max=3,
            step=0.5,
            value=1,
            id="fc-slider"
        )
    ]),
    html.Br(),
    html.Table([
        html.Tr([
            html.Th("p-value correction"),
            html.Th("N/A action"),
            html.Th("NSAF processing"),
        ]),
        html.Tr([
            html.Td(
                dcc.RadioItems([
                    "Use bonferroni correction",
                    "Use raw p-value"
                ], id="bonferroni", value="Use bonferroni correction"),
            ),
            html.Td(
                dcc.RadioItems([
                    "Remove N/A",
                    "Set N/A to min value"
                ], id="usena", value="Set N/A to min value"),
            ),
            html.Td(
                dcc.RadioItems([
                    "Use log(NSAF)",
                    "Use raw NSAF"
                ], id="lognsaf", value="Use log(NSAF)"),
            ),
        ])
    ], style={'margin-left':'auto', 'margin-right':'auto'}),
    html.Br(),
    html.Div([
        dcc.Loading(dcc.Graph(id="volcano-plot"), type="graph"),
        dcc.Loading(html.Img(id="string_svg", style={"display": "block", "margin-left": "auto", "margin-right": "auto", 'max-width': '100%'}), type="circle"),
        html.Table([
            html.Tr([
                html.Td(html.P("Copy diff. expressed")),
                dcc.Clipboard(id="proteins_copy"),
                html.Td(html.P("Copy background")),
                dcc.Clipboard(id="background_copy"),
            ])
        ]),
        dash_table.DataTable(
            id="result_proteins_table",
            columns=[
                {"name": "Protein", "id": "dbname"},
                {"name": "Fold Change", "id": "FC"},
                {"name": "p-value", "id": "logp"},
            ],
            style_cell_conditional=[
                {
                    'if': {'column_id': 'dbname'},
                    'textAlign': 'left'
                }
            ])
    ])
], style={'margin-left': "20%", 'margin-right': "20%"})

@callback(
    Output("proteins_copy", "content"),
    Input("proteins_copy", "n_clicks"),
    State("result_proteins_table", "data")
)
def copy_proteins(_, data):
    """Copy filtered proteins' dbnames"""
    dff = pd.DataFrame(data)
    print(dff.columns)
    if "dbname" in dff.columns:
        return "\n".join(dff.sort_values("logp")["dbname"].apply(lambda s: s.split("|")[1]).to_list())
    return ""

@callback(
    Output("background_copy", "content"),
    Input("background_copy", "n_clicks"),
    State("experiment", "value")
)
def copy_proteins(_, value):
    """Copy background proteins' dbnames"""
    with open(os.path.join("background", "{}.txt".format(value))) as f:
        return f.read()

@callback(
    Output("string_svg", "src"),
    Input("result_proteins_table", "data")
)
def update_string_img(data):
    """Show string plot for filtered proteins"""
    dff = pd.DataFrame(data)
    if "dbname" not in dff.columns:
        return ""
    li = dff["dbname"].apply(lambda s: s.split("|")[1]).to_list()
    return get_string_svg(li)
    

@callback(
    Output("volcano-plot", "figure"),
    Output("result_proteins_table", "data"),
    Output("file_err", "children"),
    Input("experiment", "value"),
    Input("p-value-slider", "value"),
    Input("fc-slider", "value"),
    Input("bonferroni", "value"),
    Input("usena", "value"),
    Input("lognsaf", "value")
)
def update_plot(experiment, p_value, fc, bnf, na, lognsaf):
    """Apply filters and use specified methods to build volcano-plot"""
    lognsaf = "Use log(NSAF)" in lognsaf
    path = os.path.join("plot_data_b", "{}{}.csv".format(experiment, "_l" if lognsaf else ""))
    if os.path.exists(path):
        data = pd.read_csv(path)
    else:
        data = fcp(get_data(experiment, lognsaf))
        data.to_csv(path)
    if experiment not in file_data["Sample"].to_list():
        return no_update, no_update, "Files not found"
    if not os.path.exists(os.path.join("background", "{}.txt".format(experiment))):
        data["FC_abs"] = data["FC"].apply(abs)
        with open(os.path.join("background", "{}.txt".format(experiment)), "w") as f:
            f.write("\n".join(data.sort_values("FC_abs")["dbname"].apply(lambda s: s.split("|")[1]).to_list()))
    bnf = bnf == "Use bonferroni correction"
    na = na == "Remove N/A"
    p_value = [0.001, 0.005, 0.01, 0.05, 0.1, 0.5][int(p_value)]
    dff = data[~data["wasna"]] if na else data
    p_threshold = -np.log10(p_value/len(dff)) if bnf else -np.log10(p_value)
    dff["alpha"] = dff.apply(lambda row: (1 if (row.logp > p_threshold) and (abs(row.FC) > fc) else 0.05), axis=1)

    # fig = px.scatter(dff, x='FC', y='logp', hover_data="wasna", color="sample", hover_name="dbname", height=750, opacity="alpha")
    # fig.add_hline(p_threshold, fillcolor='red')
    # fig.add_vline(-1*fc, fillcolor='red')
    # fig.add_vline(fc, fillcolor='red')
    fig = dash_bio.VolcanoPlot(
        data,
        "FC",
        "pvalue",
        "dbname",
        "dbname",
        xlabel="FC",
        effect_size_line=[-fc, fc],
        genomewideline_value=p_threshold,
        height=750
    )

    relevant: pd.DataFrame = data[(data['logp'] > p_threshold) & (data['FC'].apply(abs) > fc)]
    proteins = relevant["dbname"].apply(lambda s: s.split("|")[1]).to_list()
    
    return fig, relevant[["dbname", "FC", "logp"]].to_dict('records'), ""

if __name__ == "__main__":
    app.run(debug=True)