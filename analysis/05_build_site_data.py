"""Build a static data bundle from versioned aggregates; no private data."""
from pathlib import Path
import json,pandas as pd
P=Path(__file__).resolve().parents[1]
files={'europe':'europe_priorities_country.csv','eu_mean':'europe_priorities_mean.csv','ess':'ess_hardship_country.csv','ess_overlap':'ess_hardship_overlap.csv','ess_groups':'ess_four_groups.csv','spain_pilot':'spain_text_pilot.csv','us_media_public':'us_media_public_agenda.csv','spain_frontpages':'spain_frontpage_2000_2011.csv','spain_benchmark':'spain_cap_dictionary_benchmark.csv','brazil_mip':'brazil_mip_longitudinal.csv','six_euro':'six_country_euro_priorities.csv','manifesto_focus':'manifesto_focus_longitudinal.csv','macro_panel':'macro_issue_panel.csv','spain_macro':'spain_macro_conditions.csv','ess_trust':'ess_insecurity_trust_country.csv','cis_identity':'identity_spain_cis_selected.csv','structure':'structural_exposure_wdi.csv','ess_summary':'ess_hardship_summary.csv','ess_model':'ess_hardship_model.csv','manifesto':'manifesto_issue_shares.csv','nyt':'nyt_topics_2010_2016.csv','mecco':'mecco_baskets_annual.csv'}
result={}
for key,file in files.items():
 d=pd.read_csv(P/'data/processed'/file).astype(object).where(lambda x:pd.notnull(x),None)
 result[key]=d.to_dict('records')
for key,file in {'ess_full':'ess_full_country_changes.csv','inflation_model':'inflation_models.csv','wbl':'wbl_legal_2010_2023.csv','ember':'ember_renewables_2010_2025.csv'}.items():
 d=pd.read_csv(P/'analysis/baseline/outputs'/file).astype(object).where(lambda x:pd.notnull(x),None)
 result[key]=d.to_dict('records')
(P/'docs/data.js').write_text('window.RESEARCH_DATA='+json.dumps(result,ensure_ascii=False,allow_nan=False)+';\n',encoding='utf-8')
print('Built static data for',len(result),'tables')
