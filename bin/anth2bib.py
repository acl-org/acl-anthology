#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ../bin/anth2bib.py > all.bib

# reads all .xml files in current directory
# and prints bibtex entries to stdout

import os
import re, sys
import xml.etree.ElementTree as ET
import codecs
# file latex.py should be in the same directory as this python script
import latex

# register latex as a codec
latex.register()

# convert xml entry to string
def author_string(author):
  author_s = ""
  if (author.findall("last") and author.find("last").text):
    author_s += author.find("last").text
  if (author.findall("first") and author.find("first").text):
    author_s += ", " + author.find("first").text
  # should not have quotes in names
  if re.search(r"\"", author_s):
    sys.stderr.write("warning: quotes in name: " + author_s + "\n")
    author_s = re.sub(r"\"", "''", author_s) 
  # convert accents to latex escapes
  author_str = codecs.encode(author_s, "latex")
  return author_str

# takes an xml element
# converts tags specified in schema.rnc
#  <fixed-case> to curly braces
#  <b> to \textbf
#  <i> to \textit
#  <tex-math> to $ $
#  <url> to \url
# returns a latex-format string or None if there is no text
def convert_xml_text_markup(title):
  for elem in title.findall(".//fixed-case"):
    elem.text = "{" + elem.text + "}"
  for elem in title.findall(".//b"):
    elem.text = "\\textbf{" + elem.text + "}"
  for elem in title.findall(".//i"):
    elem.text = "\\textit{" + elem.text + "}"
  for elem in title.findall(".//tex-math"):
    elem.text = "$" + elem.text + "$"
  for elem in title.findall(".//url"):
    elem.text = "\\url{" + elem.text + "}"
  if title.text:
    # this removes any xml markup within the title string, but keeps all text
    title = "".join(title.itertext()).strip()
    title = re.sub(r"\"\b", "``", title)
    title = re.sub(r"\"", "''", title)
    return title
  else:
    return None

# takes references to <paper> and <volume> xml entries
# prints bibtex entry
def printbib(item, volume, file=sys.stdout):
  volume_id = volume.get("id")
  paper_id = item.get("id")
  if (volume_id[0] == "Q" or volume_id[0] == "J"):
    bibtype = "@Article"
    print ( "@Article{" + volume_id + '-' + item.get("id") + ",", file=file )
  else:
    if (paper_id[-3:] == "000" or
        (volume_id[0] == "W" and paper_id[-2:] == "00")):
      bibtype = "@Proceedings"
      print ( "@Proceedings{" + volume_id + '-' + item.get("id") + ",", file=file )
    else:
       bibtype = "@InProceedings"
       print ( "@InProceedings{" + volume_id + '-' + item.get("id") + ",", file=file )
  for title in item.findall('title'):
    title = convert_xml_text_markup(title)
    if title:
      print ( u"  title = \"" + title + u"\",", file=file )

      
  if item.find("author"):
    file.write( "  author = \"" )
    s=' and\n            '
    print( s.join(map(author_string, item.findall("author"))) +
           "\",", file=file )

  if item.find("editor"):
    file.write( "  editor = \"" )
    s=' and\n            '
    print( s.join(map(author_string, item.findall("editor"))) +
           "\",", file=file )

  if (volume_id[0] == "Q" or volume_id[0] == "J"):
    # journals
    year = int(volume_id[1:3])
    if year > 60:
      year += 1900
    else:
      year += 2000
    volume_title = volume.find('paper').find('title').text
    journal_name = volume_title
    # volume numbers for journal articles
    if (volume.find("volume")):
      # <volume> tag in xml file takes precedence
      journal_volume = volume.find("volume").text
    elif volume_id[0] == 'J' and year > 1979:
      # if <volume> tag not found, convert year to volume number for CL
      journal_volume = str( year - 1974 )
      # replace "Computational Linguistics, Volume 18, Issue 1"
      # with    "Computational Linguistics"
      journal_name = re.sub("[-–, ]*Volume .*", '', volume_title)
    elif volume_id[0] == 'Q':
      # convert year to volume number for TACL
      journal_volume = str( year - 2012 )
      journal_name = re.sub("[-–, ]*Volume .*", '', volume_title)
    else:
      journal_volume = False

    # issue numbers for journal articles
    if (volume.find("issue")):
      # <issue> tag in xml file takes precedence
      journal_issue = volume.find("issue").text
    elif volume_id[0] == 'J':
      # otherwise, the thousands place in the paper id is the issue number for CL
      journal_issue = str( int(item.get("id")) // 1000 )
    else:
      journal_issue = False
      # TACL has no issue number

    if journal_name:
      print ( "  journal = \"" + journal_name + "\",", file=file )
    if journal_volume:
      print ( "  volume = \"" + journal_volume + "\",", file=file )
    if journal_issue:
      print ( "  number = \"" + journal_issue + "\",", file=file )
  else:
    # this is a proceedings, not a journal 
    if item.findall('booktitle'):
      for i in item.findall('booktitle'):
        if i.text:
          print ( "  booktitle = \"" + i.text.strip() + "\",", file=file )
    elif not bibtype == "@Proceedings":
      # fall back to <title> in first paper in <volume>
      for i in volume.find('paper').findall('title'):
        if i.text:
          print ( "  booktitle = \"" + i.text.strip() + "\",", file=file )

  for i in item.findall('month'):
    print ( "  month = \"" + i.text + "\",", file=file )
  for i in item.findall('year'):
    print ( "  year = \"" + i.text + "\",", file=file )

  for i in item.findall('address'):
    print ( "  location = \"" + i.text + "\",", file=file )

  for i in item.findall('publisher'):
    print ( "  publisher = \"" + i.text + "\",", file=file )

  for i in item.findall('pages'):
    if i.text:
      pagerange = re.sub(u"[–-]+", "--", i.text)
      print ( u"  pages = \"" + pagerange + "\",", file=file )

  for i in item.findall('url'):
    print ( "  url = \"" + i.text + "\",", file=file )
    
  for i in item.findall('doi'):
    print ( "  doi = \"" + i.text + "\",", file=file )

  for i in item.findall('abstract'):
    abstract = convert_xml_text_markup(i)
    if (abstract == None):
      continue
    if len(re.findall(r"\{", abstract)) != len(re.findall(r"\}", abstract)):
      sys.stderr.write("warning: unbalanced braces in abstract: " + volume_id + " " + item.get("id") + "\n")
      sys.stderr.write("  " + "".join(re.findall(r"\{", abstract)) + " " + "".join(re.findall(r"\}", abstract)) + "\n")
    print ( "  abstract = \"" + abstract + "\",", file=file )

  print( "}", file=file)
                        
count = 0
for f in os.listdir('.'):
  if f.endswith(".xml"):	# *.xml in current directory
    tree = ET.parse(f)
    root = tree.getroot()
    volume_id = root.get("id")
    for item in root.findall('paper'): 
      printbib(item, root)
      print ()
