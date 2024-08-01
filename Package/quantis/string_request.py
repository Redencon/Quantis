"""Function to request svg from STRING"""
import requests as rqt
import base64

def get_string_svg(proteins, species, required_score=None):
    """Get html-injectable svg of a String plot for given set of proteins
    
    Based on `show_string_picture` function from
    https://github.com/kazakova/Metrics/blob/main/QRePS/stattest_metrics.py
    """
    if not proteins:
        return ""
    # if len(proteins) > 40:
    #     return ""
    string_api_url = "https://string-db.org/api/"
    output_format = "svg"
    method = "network"
    request_url = string_api_url + output_format + "/" + method
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
        return ""
    return 'data:image/svg+xml;base64,{}'.format(base64.b64encode(res.content).decode())