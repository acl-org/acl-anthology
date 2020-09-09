from anthology.utils import deconstruct_anthology_id
import pandas as pd
import os
import lxml.etree as ET
import glob

script_root = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_root, "../data/xml")

def combine_tsv():
    extension = 'tsv'
    all_fnames = [i for i in glob.glob('*.{}'.format(extension))]
    print("Using the following files:", all_fnames)
    combined_df = pd.concat([pd.read_csv(os.path.join(script_root, fname), sep="\t") for fname in all_fnames])
    # print(combined_df.shape)
    return combined_df

def split_anth_id(id):
    (coll_id, vol_id, paper_id) = deconstruct_anthology_id(id)
    # if coll_id == "2020.acl":
        # return '{0}-{1}'.format(coll_id, vol_id)
    # else:
    return coll_id

def add_video_tag(anth_paper, xml_file):
    coll_id, vol_id, paper_id = deconstruct_anthology_id(anth_paper.anthology_id)
    tree = ET.parse(os.path.join(data_dir, xml_file))
    # print(tree.getroot())

    paper = tree.getroot().find(f'./volume[@id="{vol_id}"]/paper[@id="{paper_id}"]')
    video_url = "http://slideslive.com/{}".format(anth_paper.presentation_id)
    sub_ele = ET.SubElement(paper, "video", tag="video", href=video_url)
    sub_ele.text=''
    sub_ele.tail="\n"
    paper.insert(-2, sub_ele)
    # ET.dump(paper)
    with open(os.path.join(data_dir, coll_id + ".xml"), 'wb') as f:
        tree.write(f)


def main():
    combo_df = combine_tsv()
    combo_df_uniques = combo_df['anthology_id'].apply(split_anth_id).unique()
    # print(combo_df_uniques)

    for xml in os.listdir(data_dir):
        fname, ext = os.path.splitext(xml)
        if fname in combo_df_uniques.tolist() or fname == "2020.acl":
            df_subset = combo_df[combo_df['anthology_id'].str.startswith(fname)]
            print(df_subset)
            df_subset.apply(add_video_tag, axis=1, xml_file=xml)


if __name__ == '__main__':
    main()