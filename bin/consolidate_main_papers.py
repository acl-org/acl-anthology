import os
import pandas as pd

def split_url(url):
    res = url.rsplit('/', 1)
    res = res[1].rsplit('.', 1)
    # print(res)
    return pd.Series({
        'anthology_id': res[0]
    })


PROJ_ROOT = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(PROJ_ROOT, "acl-2020-virtual-conference-sitedata")
# print(data_dir)

papers = [ "main_papers.csv", "srw_papers.csv", "demo_papers.csv" ]
slides = [ "main_paper_slideslive_ids.csv", "srw_paper_slideslive_ids.csv", "demo_paper_slideslive_ids.csv" ]

temp_df1 = pd.read_csv(os.path.join(data_dir, "srw_papers.csv"))
temp_df2 = pd.read_csv(os.path.join(data_dir, "srw_paper_slideslive_ids.csv"))

res_df = pd.merge(temp_df1, temp_df2, on="UID")
res_df = res_df[['UID', 'presentation_id', 'title', 'pdf_url', 'authors', 'abstract', 'keywords', 'track', 'paper_type']]
# split_url('https://www.aclweb.org/anthology/2020.acl-main.8.pdf')
print(res_df['pdf_url'])

# for NaN values in srw_papers.csv
res_df = res_df[res_df['pdf_url'].notnull()]
# print(new_df['pdf_url'])

anth_df = res_df['pdf_url'].apply(split_url)
final_df = pd.concat([res_df, anth_df], axis=1)
# print(final_df[0:5])
final_df.to_csv('srw_full.tsv', sep='\t', index=False)
header = [ "anthology_id", "presentation_id"]
final_df.to_csv('srw.tsv', sep='\t', index=False)

# Columns in main_papers.csv
# ['UID', 'title', 'authors', 'abstract', 'keywords', 'track', 'paper_type', 'pdf_url', 'presentation_id']
# Columns in srw_papers.csv
# ['UID', 'title', 'authors', 'abstract', 'keywords', 'track', 'paper_type', 'pdf_url', 'presentation_id']
# Columns in demo_papers.csv
# ['UID', 'title', 'authors', 'abstract', 'keywords', 'track', 'paper_type', 'pdf_url', 'demo_url', 'presentation_id']