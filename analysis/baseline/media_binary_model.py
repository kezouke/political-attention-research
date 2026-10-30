from pathlib import Path
import numpy as np,pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import precision_recall_fscore_support, precision_recall_curve, average_precision_score
BASE=Path(__file__).resolve().parent
raw=pd.read_csv(BASE/'data/nyt.csv',encoding='latin1',low_memory=False)
d=raw[raw.year.between(1996,2016)&raw.Description.notna()&raw.majortopic.notna()].copy()
a=d[d.year<=2005];val=d[d.year.between(2006,2009)];tr=d[d.year<=2009];te=d[d.year>=2010]
rows=[]
for label,code in [('environment',7),('civil_rights',2),('economy',1)]:
 def model():return make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_df=.9,sublinear_tf=True,strip_accents='unicode'),LogisticRegression(C=1,max_iter=1000,class_weight='balanced'))
 m=model().fit(a.Description,(a.majortopic==code).astype(int)); pr=m.predict_proba(val.Description)[:,1];precision,recall,thresholds=precision_recall_curve((val.majortopic==code).astype(int),pr);f1=2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1],1e-10);threshold=float(thresholds[np.argmax(f1)])
 m=model().fit(tr.Description,(tr.majortopic==code).astype(int));y=(te.majortopic==code).astype(int);scores=m.predict_proba(te.Description)[:,1]; pred=(scores>=threshold).astype(int);p,r,f,s=precision_recall_fscore_support(y,pred,average='binary',zero_division=0)
 rows.append({'label':label,'train_n':len(tr),'validation_n':len(val),'test_n':len(te),'test_positives':int(y.sum()),'threshold':threshold,'precision':p,'recall':r,'f1':f,'test_avg_precision':average_precision_score(y,scores),'test_predicted_positives':int(pred.sum())})
pd.DataFrame(rows).to_csv(BASE/'outputs/nyt_binary_temporal_validation.csv',index=False);print(pd.DataFrame(rows).round(3).to_string(index=False))
