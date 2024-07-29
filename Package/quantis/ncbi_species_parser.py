"""Fetch species name by taxonomy ID from NCBI database."""
import requests
import xml.etree.ElementTree as ET


def fetch_species_name(taxid: int|str) -> str:
    """Fetch species name by taxonomy ID from NCBI database."""
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=taxonomy&id={taxid}"
    response = requests.get(url)
    response.raise_for_status()
    data = ET.fromstring(response.text)
    for item in data[0]:
        if item.tag == 'Item' and item.attrib['Name'] == 'ScientificName':
            name = item.text
            break
    else:
        raise ValueError(f"Species name not found for taxid: {taxid}")
    if name is None:
        raise ValueError(f"Species name not found for taxid: {taxid}")
    np = name.split(' ')
    name = "{} {}".format(
        (np[0][0]+"." if np[0][0].isupper() and len(np) > 1 else np[0]),
        " ".join(np[1:])
    )
    return name


if __name__ == "__main__":
    import sys
    taxid = int(sys.argv[1])
    print(fetch_species_name(taxid))