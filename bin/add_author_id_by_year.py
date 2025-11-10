# example usage: python add_author_id.py author_id first_name last_name 2019 2021 2025

from lxml import etree
import glob
import string

def add_author_id_to_xml(file_path, first_name, last_name, id_value):
    try:
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()

        match_count = 0
        skipped_count = 0

        # XPath to find author elements in nested structure
        authors = root.xpath(".//volume/paper/author")

        for author in authors:
            first = author.find("first")
            last = author.find("last")

            if first is not None and last is not None:
                if first.text == first_name and last.text == last_name:
                    if "id" not in author.attrib:
                        author.set("id", id_value)
                        match_count += 1
                    else:
                        skipped_count += 1

        if match_count > 0:
            tree.write(file_path, encoding="utf-8", xml_declaration=True, pretty_print=False)
            print(f"[✓] {file_path}: Added id='{id_value}' to {match_count} author(s)")
            
            with open(file_path, 'rb') as f:
                data = f.read()

                if not data.endswith(b'\n'):
                    with open(file_path, 'ab') as f:  # append in binary mode
                        f.write(b'\n')



        if skipped_count > 0:
            print(f"[i] {file_path}: Skipped {skipped_count} author(s) (already had id)")

    except etree.XMLSyntaxError:
        print(f"[X] Failed to parse XML in file: {file_path}")
    except Exception as e:
        print(f"[X] Error processing {file_path}: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Add ID to matching <author> tags in XML files for given years, preserving format.")
    parser.add_argument("id", help="ID to add to the matching <author> tags")
    parser.add_argument("first", help="Author's first name to match")
    parser.add_argument("last", help="Author's last name to match")
    parser.add_argument("years", nargs="+", help="List of years (e.g., 2020 2021)")

    args = parser.parse_args()

    matching_files = []
    for year in args.years:
        matching_files.extend(glob.glob(f"{year}.*.xml"))
        yy = year[-2:]  # last two digits
        for letter in string.ascii_letters:  # includes A-Z and a-z
            matching_files.extend(glob.glob(f"{letter}{yy}*.xml"))
    matching_files = sorted(list(set(matching_files)),reverse = True, key=lambda x:x.split('.')[0][-2:])
    if not matching_files:
        print("[!] No matching XML files found for the given year(s).")
    else:
        for file_path in matching_files:
            add_author_id_to_xml(file_path, args.first, args.last, args.id)
