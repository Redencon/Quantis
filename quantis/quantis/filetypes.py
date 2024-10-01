"""Descriptions for supported filetypes

Copyright 2024 Daniil Pomogaev
SPDX-License-Identifier: Apache-2.0
"""

descriptions = {
    "Scavager": "Expected files are '..._proteins_groups.tsv' files, gropued by sample type.",
    "s+d": "Expected files are '..._proteins.tsv', '..._PFMs_ML.tsv', '..._PFMs.tsv' files for each techrep, grouped by sample type.",
    "MaxQuant": "Expected file is tab-separated table with 'iBAQ' columns and 'ProteinID' column",
    "DirectMS1Quant": "Expected file is '_quant_full.tsv' file from DirectMS1Quant output",
    "Diffacto": "Expected file is table output from Diffacto",
}