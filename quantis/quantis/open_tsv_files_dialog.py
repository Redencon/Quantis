"""Dialog functions for selecting files

Copyright 2024 Daniil Pomogaev
SPDX-License-Identifier: Apache-2.0
"""

import webview

def open_tsv_files_dialog(window: webview.Window, multiple: bool = False):
    file_types = ('TSV Files (*.tsv;*.txt)',)

    result = window.create_file_dialog(
        webview.OPEN_DIALOG, allow_multiple=multiple, file_types=file_types
    )
    return result

def open_exe_files_dialog(window: webview.Window, multiple: bool = False):
    file_types = ('Executables (*.*)',)

    result = window.create_file_dialog(
        webview.OPEN_DIALOG, allow_multiple=multiple, file_types=file_types
    )
    return result

def save_csv_file_dialog(window: webview.Window):
    file_types = ('CSV Files (*.csv)',)

    result = window.create_file_dialog(
        webview.SAVE_DIALOG, file_types=file_types, allow_multiple=False
    )
    return result