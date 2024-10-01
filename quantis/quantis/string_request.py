"""Function to request svg from STRING

Copyright 2024 Daniil Pomogaev
SPDX-License-Identifier: Apache-2.0
"""
import requests as rqt
import base64
import pandas as pd
from io import BytesIO

STRING_API_URL= "https://string-db.org/api/"

def get_string_svg(proteins, species, required_score=None):
    """Get html-injectable svg of a String plot for given set of proteins
    
    Based on `show_string_picture` function from
    https://github.com/kazakova/Metrics/blob/main/QRePS/stattest_metrics.py
    """
    if species is None or species == '-1':
        raise ValueError(f"Wrong species provided: {species}")
    if not proteins:
        return ""
    # if len(proteins) > 40:
    #     return ""
    output_format = "svg"
    method = "network"
    request_url = STRING_API_URL + output_format + "/" + method
    params = {
    "identifiers" : "%0d".join(proteins), # your protein
    "species": str(species), # species NCBI identifier
    }
    if required_score:
        irs = int(required_score)
        if irs < 0 or irs > 1000:
            raise ValueError("Required score must be between 0 and 1000")
        params["required_score"] = required_score
    try:
        res = rqt.post(request_url, params)
    except rqt.HTTPError as exception:
        raise
    return 'data:image/svg+xml;base64,{}'.format(base64.b64encode(res.content).decode())


def get_annotations(proteins, species):
    """Get GO annotations for a set of proteins"""
    output_format = "tsv"
    method = "enrichment"
    request_url = STRING_API_URL + output_format + "/" + method
    params = {
    "identifiers" : "%0d".join(proteins), # your protein
    "species": str(species), # species NCBI identifier
    }
    try:
        res = rqt.post(request_url, params)
    except rqt.HTTPError as exception:
        raise
    return pd.read_csv(BytesIO(res.content), sep="\t").sort_values("fdr")


def get_string_ids(proteins, species) -> list[str]:
    """Get STRING IDs for a set of proteins"""
    output_format = "tsv"
    method = "get_string_ids"
    request_url = STRING_API_URL + output_format + "/" + method
    params = {
    "identifiers" : "%0d".join(proteins), # your protein
    "species": str(species), # species NCBI identifier
    "limit": 1
    }
    try:
        res = rqt.post(request_url, params)
    except rqt.HTTPError as exception:
        raise
    if "Error" in str(res):
        raise ValueError("StringDB request resulted in error:\n{}".format(str(res)))
    df = pd.read_csv(BytesIO(res.content), sep="\t")
    if 'stringId' not in df.columns:
        raise ValueError("stringId column not found. DataFrame columns:\n{}\n\n{}".format(df.columns, df))
    return df['stringId'].tolist()