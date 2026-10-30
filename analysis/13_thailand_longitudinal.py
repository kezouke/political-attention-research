"""Thailand: documented 2009–10 comparison and election arithmetic.

The published source tables are hand-transcribed, not automatic annotations.
This is not a single combined survey time series, and cannot assign motives to voters.
The 2010 economy value is deliberately omitted: source text, summary and chart conflict.
"""
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parents[1]
U='https://www.locjkt.or.id/application/docliblcjkt/upload/ThailandNationalSurvey2010.pdf'
rows=[
 {'survey':'Asia Foundation national electorate','fieldwork':'2009-06-13 to 2009-07-05','year':2009,'question':'In your view, what is the biggest problem facing Thailand?','issue':'political conflict','percent':24.0,'n':1500,'population':'voting age, excluding Pattani, Yala and Narathiwat','source_url':U,'source_page':'25','comparable_group':'asia_foundation_2009_2010'},
 {'survey':'Asia Foundation national electorate','fieldwork':'2009-06-13 to 2009-07-05','year':2009,'question':'In your view, what is the biggest problem facing Thailand?','issue':'poor economy','percent':60.0,'n':1500,'population':'voting age, excluding Pattani, Yala and Narathiwat','source_url':U,'source_page':'25','comparable_group':'asia_foundation_2009_2010'},
 {'survey':'Asia Foundation national electorate','fieldwork':'2010-09-17 to 2010-10-23','year':2010,'question':'In your view, what is the biggest problem facing Thailand?','issue':'political conflict','percent':42.0,'n':1500,'population':'voting age, excluding Pattani, Yala and Narathiwat for comparison','source_url':U,'source_page':'25','comparable_group':'asia_foundation_2009_2010'},
 {'survey':'Asia Foundation national electorate','fieldwork':'2010-09-17 to 2010-10-23','year':2010,'question':'In your view, what is the biggest problem facing Thailand?','issue':'poor economy','percent':None,'n':1500,'population':'voting age, excluding Pattani, Yala and Narathiwat for comparison','source_url':U,'source_page':'9,25','comparable_group':'asia_foundation_2009_2010'},
 {'survey':'Thammasat / Marketbuzzz','fieldwork':'2021; dates undisclosed','year':2021,'question':'public concerns; original questionnaire unavailable','issue':'environment','percent':38.0,'n':1000,'population':'surveyed Thai people; recruitment and survey mode undisclosed','source_url':'https://sgs.tu.ac.th/news/the-mas-program-the-school-of-global-studies-thammasat-university-and-marketbuzz-collaborated-on-the-survey-topic-are-the-majority-of-thai-people-concerned-about-the-environment/','source_page':'article','comparable_group':'not_established'},
 {'survey':'Thammasat / Marketbuzzz','fieldwork':'2023-04; exact days undisclosed','year':2023,'question':'top public concerns; original questionnaire unavailable','issue':'environment','percent':42.0,'n':1000,'population':'surveyed Thai people; recruitment and survey mode undisclosed','source_url':'https://sgs.tu.ac.th/news/top-public-concern-in-thailand-2023/','source_page':'article','comparable_group':'not_established'},
 {'survey':'Gallup World Poll','fieldwork':'2025-09 to 2025-11','year':2025,'question':'single most important problem facing country, open-ended','issue':'economy','percent':48.0,'n':None,'population':'Thai people; country-specific sample size not in release','source_url':'https://news.gallup.com/poll/701897/economy-dominates-issues-ahead-thai-election.aspx','source_page':'article','comparable_group':'not_established'},
 {'survey':'Gallup World Poll','fieldwork':'2025-09 to 2025-11','year':2025,'question':'single most important problem facing country, open-ended','issue':'safety and security','percent':13.0,'n':None,'population':'Thai people; country-specific sample size not in release','source_url':'https://news.gallup.com/poll/701897/economy-dominates-issues-ahead-thai-election.aspx','source_page':'article','comparable_group':'not_established'}]
pd.DataFrame(rows).to_csv(P/'data/processed/thailand_public_opinion_snapshots.csv',index=False)
# Rounding sensitivity only: published shares have no decimals. It is not a CI.
diff=42-24
pd.DataFrame([{'survey':'Asia Foundation 2009 vs 2010, matched geography','issue':'political conflict','first_year':2009,'last_year':2010,'first_pct':24,'last_pct':42,'change_pp':diff,'rounding_lower_pp':17,'rounding_upper_pp':19,'uncertainty_note':'Assumes each published integer rounded to nearest percentage point. Not a sampling CI; study uses stratified clusters.'}]).to_csv(P/'data/processed/thailand_issue_change_2009_2010.csv',index=False)
# The party-choice denominator excludes "no party" ballots in both ECT sources.
URL23='https://www.ect.go.th/ect_th/th/db_119_ect_th_cms_1/4749'
URL26='https://www.ect.go.th/web-upload/1xff0d34e409a13ef56eea54c52a291126/tinymce/106-2304f1b39872ea67026a850d0630fa8b/%E0%B8%82%E0%B9%88%E0%B8%B2%E0%B8%A7%20%E0%B8%AA%E0%B8%AA%2069/203-%202569%20%20%E0%B8%AA%E0%B8%A3%E0%B8%B8%E0%B8%9B%E0%B8%82%E0%B9%89%E0%B8%AD%E0%B8%A1%E0%B8%B9%E0%B8%A5%E0%B8%81%E0%B8%B2%E0%B8%A3%E0%B9%80%E0%B8%A5%E0%B8%B7%E0%B8%AD%E0%B8%81%E0%B8%95%E0%B8%B1%E0%B9%89%E0%B8%87%20%E0%B8%AA%E0%B8%AA-%E0%B9%81%E0%B8%9A%E0%B8%9A%E0%B9%81%E0%B8%9A%E0%B9%88%E0%B8%87%E0%B9%80%E0%B8%82%E0%B8%95%E0%B9%80.pdf'
parties=[(2023,'Move Forward',14438851,37522746,151,URL23),(2023,'Pheu Thai',10962522,37522746,141,URL23),(2023,'Bhumjaithai',1138202,37522746,71,URL23),(2026,'People’s Party',11043309,35030579,120,URL26),(2026,'Pheu Thai',5575456,35030579,74,URL26),(2026,'Bhumjaithai',6468073,35030579,192,URL26)]
e=[]
for year,party,votes,total,seats,url in parties:
 e.append({'year':year,'party':party,'party_list_votes':votes,'party_choice_votes_total':total,'party_choice_vote_pct':100*votes/total,'total_seats':seats,'house_seats':500,'seat_pct':100*seats/500,'source_ect':url,'seat_source':'https://data.ipu.org/parliament/TH/TH-LC01/election/TH-LC01-E20230514/' if year==2023 else 'https://data.ipu.org/parliament/TH/TH-LC01/election/TH-LC01-E20260208/'})
E=pd.DataFrame(e);E.to_csv(P/'data/processed/thailand_election_results.csv',index=False)
print('Political conflict 2009 to 2010: +18 pp (17–19 pp considering integer rounding alone)')
print(E[['year','party','party_choice_vote_pct','total_seats','seat_pct']].round(2).to_string(index=False))
