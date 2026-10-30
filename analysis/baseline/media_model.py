from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report, confusion_matrix
BASE=Path(__file__).resolve().parent
raw=pd.read_csv(BASE/'data/nyt.csv',encoding='latin1',low_memory=False)
d=raw[raw.year.between(1996,2016) & raw.Description.notna() & raw.majortopic.notna()].copy()
codes={1:'economy',2:'civil_rights',7:'environment',8:'energy',9:'immigration',12:'crime',16:'defence',19:'international',20:'government'}
d['label']=d.majortopic.map(codes).fillna('other')
train=d[d.year<=2009];test=d[d.year>=2010]
clf=make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=3,max_df=.9,sublinear_tf=True,strip_accents='unicode'),LogisticRegression(C=2,class_weight='balanced',max_iter=1000))
clf.fit(train.Description,train.label)
pred=clf.predict(test.Description)
metrics=pd.DataFrame(classification_report(test.label,pred,output_dict=True,zero_division=0)).T;metrics.to_csv(BASE/'outputs/nyt_model_metrics.csv')
labels=sorted(d.label.unique());pd.DataFrame(confusion_matrix(test.label,pred,labels=labels),index=labels,columns=labels).to_csv(BASE/'outputs/nyt_model_confusion.csv')
test=test.assign(pred=pred); by=test.groupby(['year','label']).size().unstack(fill_value=0);py=test.groupby(['year','pred']).size().unstack(fill_value=0);by.to_csv(BASE/'outputs/nyt_test_human_counts.csv');py.to_csv(BASE/'outputs/nyt_test_predicted_counts.csv')
print('TRAIN',len(train),'TEST',len(test),'1996-2009 train, 2010-2016 held out');print(metrics.round(3).to_string())
