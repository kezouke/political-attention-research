import pandas as pd
from pathlib import Path
p=Path(__file__).resolve().parent
x=pd.DataFrame([{'year':2014,'environment':901,'economy':443,'other':24,'missing':118},{'year':2018,'environment':957,'economy':484,'other':43,'missing':278}]);x['total']=x[['environment','economy','other','missing']].sum(axis=1);x['environment_all']=100*x.environment/x.total;x['environment_two_choices']=100*x.environment/(x.environment+x.economy);x['missing_pct']=100*x.missing/x.total;x.to_csv(p/'outputs/wvs_brazil_denominators.csv',index=False,float_format='%.6f');print(x.round(2).to_string(index=False));print('changes',x.environment_all.iloc[1]-x.environment_all.iloc[0],x.environment_two_choices.iloc[1]-x.environment_two_choices.iloc[0])
