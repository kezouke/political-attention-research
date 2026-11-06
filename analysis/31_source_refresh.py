"""Verify whether the 2026 crisis update adds an intervening crisis.

The downloadable ZIP returned HTTP 404; the official PDF table is retained
locally and its 13 additions are extracted with a checked country crosswalk.
The historical 2020 baseline is preserved, not silently replaced.
"""
import hashlib
import json
import re
from pathlib import Path
import fitz
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/processed'
URL='https://www.imf.org/-/media/files/publications/wp/2026/english/wpiea2026094-source-pdf.pdf'
ISO={'Angola':'AGO','Azerbaijan':'AZE','Chad':'TCD','Equatorial Guinea':'GNQ','Ghana':'GHA',
     'Kazakhstan':'KAZ','Lebanon':'LBN','Nicaragua':'NIC','Republic of the Congo':'COG',
     'São Tomé and Príncipe':'STP','Sri Lanka':'LKA','Tajikistan':'TJK','Vietnam':'VNM'}


def main():
    path=ROOT/'data/raw/laeven_valencia_2026.pdf'
    doc=fitz.open(path);text=doc[8].get_text()
    table=text.split('Table 1. New episodes relative to Laeven and Valencia (2020)')[1].split('* Denotes borderline cases')[0]
    rows=[]
    for name,iso in ISO.items():
        match=re.search(re.escape(name)+r'(\*)?\s+(\d{4})',table)
        if not match:raise ValueError(name)
        rows.append(dict(country=name,iso=iso,year=int(match[2]),borderline=bool(match[1]),pdf_page=9))
    additions=pd.DataFrame(rows);assert len(additions)==13
    additions.to_csv(OUT/'banking_2026_additions.csv',index=False)
    primary=pd.read_csv(OUT/'crisis_dynamics_balanced.csv')
    controls=pd.read_csv(OUT/'crisis_dynamics_calm.csv')
    overlap=set(additions.iso)&(set(primary.iso)|set(controls.iso))
    audit=dict(source=URL,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),new_episodes=13,
               overlap_with_banking_or_calm_countries=sorted(overlap),
               interpretation='No newly listed episode affects the analysed trajectories. Historical dates/definitions remain the frozen 2020 edition.')
    (OUT/'banking_source_refresh.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(audit)


if __name__=='__main__':main()
