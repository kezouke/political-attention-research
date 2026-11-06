"""Temporal benchmark: lexical classifier versus frozen multilingual BERT.

CAP provides external reference labels. The classifier is selected on 2004,
then evaluated once on 2008. No LLM-generated labels are treated as human truth.
Model weights, embeddings and source statements remain local.
"""
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, log_loss

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT/'data/raw', ROOT/'data/processed'
MODEL = 'intfloat/multilingual-e5-small'
MODEL_REVISION = '614241f622f53c4eeff9890bdc4f31cfecc418b3'
GROUPS = {'economy': [1,5,15], 'material_broad': [1,3,5,6,13,14,15],
          'environment': [7], 'civil_rights': [2], 'government': [20]}


def load_data():
    d = pd.read_csv(RAW/'cap_spain_manifestos.csv').dropna(subset=['year','majortopic','sentence text']).copy()
    d['text'] = d['sentence text'].str.strip()
    d = d[d.text.str.len().gt(0) & d.majortopic.between(1, 99)].copy()
    d['label'] = d.majortopic.astype(int)
    d['norm'] = d.text.str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
    # Exclude exact repetitions across documents from training/selection.
    future = set(d.loc[d.year.ge(2004),'norm'])
    test_text = set(d.loc[d.year.eq(2008),'norm'])
    d['split'] = np.where(d.year.eq(2008), 'test', np.where(d.year.eq(2004), 'validation', 'train'))
    remove = (d['split'].eq('train') & d.norm.isin(future)) | (d['split'].eq('validation') & d.norm.isin(test_text))
    removed = int(remove.sum())
    return d[~remove].reset_index(drop=True), removed


def embeddings(d):
    from sentence_transformers import SentenceTransformer
    import torch
    revision = MODEL_REVISION
    digest = hashlib.sha256(('\n'.join(d.text) + revision).encode()).hexdigest()
    cache = RAW/f'cap_e5_{digest[:16]}.npz'
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    if cache.exists():
        values = np.load(cache)['embeddings']
    else:
        model = SentenceTransformer(MODEL, revision=revision, device=device, trust_remote_code=False)
        model.max_seq_length = 256
        values = model.encode(['query: '+s for s in d.text], batch_size=32,
                              normalize_embeddings=True, show_progress_bar=True)
        np.savez_compressed(cache, embeddings=values)
    return values, dict(model=MODEL, revision=revision, device=device, max_tokens=256,
                       embeddings_sha256=hashlib.sha256(values.tobytes()).hexdigest())


def evaluate(name, clf, features, d, split, c):
    mask = d['split'].eq(split).to_numpy()
    truth = d.loc[mask,'label'].to_numpy()
    prob = clf.predict_proba(features[mask])
    pred = clf.classes_[prob.argmax(axis=1)]
    stats = dict(model=name, split=split, C=c, n=len(truth), accuracy=accuracy_score(truth,pred),
                 macro_f1=f1_score(truth,pred,average='macro',zero_division=0),
                 log_loss=log_loss(truth,prob,labels=clf.classes_))
    shares = []
    for topic, codes in GROUPS.items():
        y, p = np.isin(truth,codes), np.isin(pred,codes)
        soft = prob[:, np.isin(clf.classes_,codes)].sum(axis=1)
        precision, recall, f1, _ = precision_recall_fscore_support(y,p,average='binary',zero_division=0)
        shares.append(dict(model=name,split=split,topic=topic,n=len(truth), reference_pct=100*y.mean(),
                           hard_pct=100*p.mean(),soft_pct=100*soft.mean(),
                           hard_error_pp=100*(p.mean()-y.mean()),soft_error_pp=100*(soft.mean()-y.mean()),
                           precision=precision,recall=recall,f1=f1))
    # Error IDs and hashes only, never the copyrighted statements.
    wrong = d.loc[mask,['id','year','politicalparty','text']].copy()
    wrong['reference'], wrong['predicted'] = truth, pred
    wrong = wrong[wrong.reference.ne(wrong.predicted)].head(80)
    wrong['text_sha256'] = wrong.text.map(lambda s: hashlib.sha256(s.encode()).hexdigest())
    wrong.drop(columns='text').assign(model=name,split=split).to_csv(OUT/f'nlp_errors_{name}_{split}.csv',index=False)
    return stats, shares


def main():
    start = time.time()
    d, removed = load_data()
    train = d['split'].eq('train').to_numpy()
    validation = d['split'].eq('validation').to_numpy()
    print('Splits',d.groupby(['split','year','politicalparty']).size().to_dict(),flush=True)
    vectorizer = TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=40000,sublinear_tf=True)
    vectorizer.fit(d.loc[train,'text'])
    sparse = vectorizer.transform(d.text)
    dense, metadata = embeddings(d)
    trials, metrics, shares = [], [], []
    for name, x, grid in [('tfidf',sparse,[.1,1,10]),('e5_bert',dense,[1,10,100])]:
        fitted = []
        for c in grid:
            clf = LogisticRegression(C=c,max_iter=2000,solver='lbfgs')
            clf.fit(x[train],d.loc[train,'label'])
            score = f1_score(d.loc[validation,'label'],clf.predict(x[validation]),average='macro',zero_division=0)
            trials.append(dict(model=name,C=c,validation_macro_f1=score))
            fitted.append((score,c,clf))
        _, c, clf = max(fitted,key=lambda item:item[0])
        for split in ['validation','test']:
            stat, rows = evaluate(name,clf,x,d,split,c)
            metrics.append(stat);shares.extend(rows)
        print(name,metrics[-1],flush=True)
    for rows, name in [(metrics,'nlp_metrics'),(shares,'nlp_topic_shares'),(trials,'nlp_model_selection')]:
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False,float_format='%.8g')
    metadata.update(source_sha256=hashlib.sha256((RAW/'cap_spain_manifestos.csv').read_bytes()).hexdigest(),
                    cross_split_duplicates_removed=removed, elapsed_seconds=time.time()-start,
                    train_years=sorted(d.loc[train,'year'].unique().astype(int).tolist()),
                    validation_year=2004,test_year=2008,groups=GROUPS,
                    warning='One later PSOE document; no multilingual or out-of-corpus validation. Encoder pretraining contamination is not audited.')
    (OUT/'nlp_provenance.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(pd.DataFrame(shares).query('split == "test"').round(3).to_string(index=False))


if __name__ == '__main__':
    main()
