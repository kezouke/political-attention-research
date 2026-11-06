"""Pin HF candidates and distinguish measured file contents from card claims.

No model inference or remote code execution. Metadata and aggregate schema
checks are reproducible from the acquisition manifest. Text is not republished.
"""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/audit_20261106'
OUT=ROOT/'data/processed/audit_20261106'
CANDIDATES=[
 ('dataset','parisaslanidis/populism-eu-speeches','conditional_external_validation',
  'Human sentence labels for six selected speeches, five leaders, 2014-2025. Only two speeches in 2004-2019; no ordinary-opposition comparison.',
  'Narrow selection of populist leaders. Card label-count table disagrees with downloaded file. Translation can shift rhetoric; CC BY-NC-ND requires use-specific review.'),
 ('dataset','parisaslanidis/populism-trump-2016','out_of_core_scope',
  'US 2016 speech sentence labels. Metadata/card checked, raw train/test not downloaded.',
  'Single politician and different political/language setting. Cannot validate cross-European party classification by itself.'),
 ('dataset','siacus/manifesto','reject_for_historical_panel',
  'JSONL with only text, no party/date/document identifiers.',
  'Cannot trace documents or align elections. A license tag alone does not establish underlying text provenance.'),
 ('dataset','maiammar/Manifesto_dataset','reject_as_primary_source',
  'Six manifesto documents, structured text and segmentation labels, filenames 2004/2008/2012.',
  'No adequate origin or license documentation. Ground-truth labels are not demonstrated to measure elite blame or populism.'),
 ('dataset','aarabil/clcp_manifesto','conditional_topic_training_only',
  'Entailment pairs for manifesto topic classification; sampled complete 10,000-row training split.',
  'Repeated text/hypothesis pairs are not independent documents. No party/date identifiers; unclear original-document provenance and train/test overlap.'),
 ('dataset','cjvt/ParlaMint3','supplementary_party_speech_candidate',
  'Card and loader inspected without executing. 26 comparable parliamentary corpora, mostly 2015 to mid-2022.',
  'No crisis baseline in most countries. Parliamentary statements differ from campaigns and voter exposure; country-year coverage still uncounted.'),
 ('dataset','FrancophonIA/ParlaMint_4.1','prefer_original_clarin_release',
  'Card inspected; points to CLARIN 11356/1912 and original versioned metadata. Corpus not downloaded.',
  'Mostly 2015 onwards; regions and countries are mixed. Original corpus must establish dates, license and party coverage.'),
 ('dataset','sstoeckl/populism-llm','not_accessible_verified',
  'HF API returned 401 for this candidate.',
  'No claims about content, size, annotations or permission are supported.'),
 ('model','luerhard/PopBERT','conditional_german_benchmark',
  'German Bundestag model for anti-elitism, people-centrism and host ideologies; card links 2013-2021 annotated research.',
  'No multilingual or pre-2008 validation. Original annotation download not verified; no inference run. Need held-out party/document and model-training overlap audit.'),
 ('model','manifesto-project/manifestoberta-xlm-roberta-56policy-topics-sentence-2026-1-1','conditional_topic_baseline',
  'Official 56-topic Manifesto model; card reports approximately 1.8m training statements from Manifesto 2026a.',
  'Topic labels are not populism or voter-priority labels. Historical Manifesto documents may be in training; cannot use them as independent test. Custom code not executed.'),
]

def main():
    manifest=json.loads((OUT/'acquisition_manifest.json').read_text())
    rows=[]
    for kind,repo,decision,scope,limits in CANDIDATES:
        key='hf_'+kind+'_'+repo.replace('/','__')
        rec=manifest.get(key,{})
        info=json.loads((RAW/(key+'.json')).read_text()) if rec.get('status')==200 else {}
        license=info.get('cardData',{}).get('license')
        row={'kind':kind,'repository':repo,'url':'https://huggingface.co/'+('datasets/' if kind=='dataset' else '')+repo,
             'revision':info.get('sha',''),'api_status':rec.get('status','not_acquired'),
             'license_as_metadata':json.dumps(license,ensure_ascii=False) if license else 'not_stated',
             'decision':decision,'verified_scope':scope,'limits':limits,
             'observed_rows':None,'observed_unique_texts':None,'observed_documents':None,'sample_columns':''}
        sample=next(iter(sorted(RAW.glob(key+'_sample.*'))),None)
        if sample and sample.suffix in ['.csv','.json','.parquet']:
            if sample.suffix=='.csv':d=pd.read_csv(sample)
            elif sample.suffix=='.parquet':d=pd.read_parquet(sample)
            else:d=pd.read_json(sample,lines=True)
            row['observed_rows']=len(d);row['sample_columns']='|'.join(d.columns)
            if 'text' in d and isinstance(d.text.iloc[0],str):row['observed_unique_texts']=d.text.nunique()
            if 'speech_id' in d:
                row['observed_documents']=d.speech_id.nunique()
                counts=d.groupby(['speech_id','speaker','date','location'],dropna=False).size().rename('sentences').reset_index()
                counts.to_csv(OUT/'hf_eu_speech_coverage.csv',index=False)
                d.pop_code.value_counts().sort_index().rename_axis('code').rename('sentences').to_csv(OUT/'hf_eu_speech_labels.csv')
                within=d.date.str[:4].astype(int).between(2004,2019)
                row['observed_in_2004_2019_rows']=int(within.sum())
                row['observed_in_2004_2019_documents']=d.loc[within,'speech_id'].nunique()
            if 'filename' in d:row['observed_documents']=d.filename.nunique()
        rows.append(row)
    result=pd.DataFrame(rows)
    result.to_csv(OUT/'huggingface_registry.csv',index=False)
    (OUT/'huggingface_registry.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print(result[['repository','api_status','observed_rows','observed_documents','decision']].to_string(index=False))

if __name__=='__main__':main()
