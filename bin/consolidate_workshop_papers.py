# clone the acl-anthology github repository
# git clone https://github.com/acl-org/acl-anthology.git

from anthology import Anthology
import sys, os
import re
import yaml
import pandas as pd

pd.set_option('max_columns', 500)
pd.set_option('max_rows', 500)
pd.set_option('display.max_colwidth', 1000)

anthology = Anthology(importdir='acl-anthology/data')

with open('joint.yaml', 'r') as file:
    yaml_data = yaml.full_load(file)

# print(yaml_data)
# print(yaml_data["acl"][2020])

# change stdout to a file
orig_stdout = sys.stdout

with open('anthology_dump.tsv', 'w') as f:
    sys.stdout = f

    for id, paper in anthology.papers.items():
        if paper.anthology_id.rsplit('.', 1)[0].startswith("2020.acl"):
            print(paper.anthology_id + "\t" + paper.get_title('text'))
        elif paper.anthology_id.rsplit('.', 1)[0] in yaml_data["acl"][2020]:
            print(paper.anthology_id + "\t" + paper.get_title('text'))

PROJ_ROOT = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(PROJ_ROOT, "acl-2020-virtual-conference-sitedata")
df1 = pd.read_csv(os.path.join(PROJ_ROOT, 'anthology_dump.tsv'), sep="\t", names=["anthology_id", "title"])
df1['title'] = df1['title'].str.lower()
print(df1.shape)
res_df = pd.DataFrame()
regex = r"w[0-9]+_papers.csv"
for csv_file in os.listdir(data_dir):
    match = re.search(regex, csv_file)
    if match:
        df2 = pd.read_csv(os.path.join(data_dir, csv_file))
        df2['title'] = df2['title'].str.lower()

        merged_df = pd.merge(df1, df2, on="title")

        merged_df = merged_df[['anthology_id', 'presentation_id', 'title']]
        res_df = res_df.append(merged_df)

print(res_df.shape)

header = ["anthology_id", "presentation_id"]
res_df.to_csv('workshops.tsv', mode='a', sep='\t', columns=header, index=False)