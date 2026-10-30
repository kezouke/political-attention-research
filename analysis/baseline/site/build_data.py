from pathlib import Path
import json
import pandas as pd
base=Path(__file__).resolve().parent.parent
d=pd.read_csv(base/'data/spes_aggregate.csv');d=d[d.year.between(2010,2024)]
cols=['price','unemploy','immi','env_merged','crime']
west=['Austria','Belgium','Denmark','Finland','France','Germany','Ireland','Italy','Luxembourg','Netherlands','Portugal','Spain','Sweden','United Kingdom']
c=d[d.country_name.isin(west)].groupby('year')[cols].mean().reset_index();c['country_name']='Среднее 14 стран'
d=pd.concat([d[d.country_name.isin(west+['Bulgaria','Serbia'])][['year','country_name']+cols],c]).astype(object).where(lambda x:pd.notnull(x),None)
read=lambda p:pd.read_csv(base/p).to_dict('records')
payload={'europe':d.to_dict('records'),'pew':read('data/pew_problem_trends.csv'),'wvs':read('outputs/wvs_brazil_denominators.csv'),'wvs_pair':read('outputs/wvs_2010_2020.csv'),'model':read('outputs/inflation_models.csv'),'robustness':read('outputs/inflation_robustness.csv'),'platform':read('outputs/platform_term_counts.csv'),'eu26':read('outputs/eurobarometer_2025_2026.csv'),'gdelt':read('outputs/gdelt_bbc_annual.csv'),'gdelt2':read('outputs/gdelt_matched_jan_oct.csv'),'essfull':read('outputs/ess_full_country_changes.csv'),'manifesto':read('outputs/manifesto_vote_weighted.csv'),'mecco':read('outputs/mecco_baskets_annual.csv'),'ember':read('outputs/ember_renewables_2010_2025.csv'),'wbl':read('outputs/wbl_legal_2010_2023.csv'),'ess2016':read('outputs/ess2016_ideology.csv'),'ukpolicy':read('outputs/uk_instruments_annual.csv'),'usorders':read('outputs/us_orders_2021_2025_jan20_oct15.csv'),'ukplatforms':read('outputs/uk_platform_dictionary.csv'),'ukmanifestos':read('outputs/uk_manifestos_2010_2015.csv')}
(base/'site/dist/data.js').write_text('window.RESEARCH_DATA='+json.dumps(payload,ensure_ascii=False,allow_nan=False)+';',encoding='utf-8')
