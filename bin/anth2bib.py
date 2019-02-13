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

# takes references to <paper> and <volume> xml entries
# prints bibtex entry
def printbib(item, volume):
  volume_id = volume.get("id")
  if (volume_id[0] == "Q" or volume_id[0] == "J"):
    print ( "@Article{" + volume_id + '-' + item.get("id") + "," )
  else:
    print ( "@InProceedings{" + volume_id + '-' + item.get("id") + "," )
  for title in item.findall('title'):
    if title.text:
      # this removes any xml markup within the title string, but keeps all text
      title = "".join(title.itertext()).strip()
      title = re.sub(r"\"\b", "``", title)
      title = re.sub(r"\"", "''", title)
      print ( "  title = \"" + title + "\"," )
  sys.stdout.write( "  author = \"" )
  s=' and\n            '
  print( s.join(map(author_string, item.findall("author"))) +
         "\"," )

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
      print ( "  journal = \"" + journal_name + "\"," )
    if journal_volume:
      print ( "  volume = \"" + journal_volume + "\"," )
    if journal_issue:
      print ( "  number = \"" + journal_issue + "\"," )
  else:
    # this is a proceedings, not a journal 
    if item.findall('booktitle'):
      for i in item.findall('booktitle'):
        print ( "  booktitle = \"" + i.text.strip() + "\"," )
    else:
      # fall back to <title> in first paper in <volume>
      for i in volume.find('paper').findall('title'):
        print ( "  booktitle = \"" + i.text.strip() + "\"," )

  for i in item.findall('month'):
    print ( "  month = \"" + i.text + "\"," )
  for i in item.findall('year'):
    print ( "  year = \"" + i.text + "\"," )

  for i in item.findall('address'):
    print ( "  location = \"" + i.text + "\"," )

  for i in item.findall('publisher'):
    print ( "  publisher = \"" + i.text + "\"," )

  for i in item.findall('pages'):
    if i.text:
      pagerange = re.sub(u"[–-]+", "--", i.text)
      print ( u"  pages = \"" + pagerange + "\"," )

  for i in item.findall('url'):
    print ( "  url = \"" + i.text + "\"," )
    
  for i in item.findall('doi'):
    print ( "  doi = \"" + i.text + "\"," )

  for i in item.findall('abstract'):
    abstract = "".join(i.itertext()).strip()
    abstract = re.sub(r"\"\b", "``", abstract)
    abstract = re.sub(r"\"", "''", abstract)
    if len(re.findall(r"\{", abstract)) != len(re.findall(r"\}", abstract)):
      sys.stderr.write("warning: unbalanced braces in abstract: " + volume_id + " " + item.get("id") + "\n")
      sys.stderr.write("  " + "".join(re.findall(r"\{", abstract)) + " " + "".join(re.findall(r"\}", abstract)) + "\n")
    print ( "  abstract = \"" + abstract + "\"," )

  print( "}")
                        
count = 0
for f in os.listdir('.'):
  if f.endswith(".xml"):	# *.xml in current directory
    tree = ET.parse(f)
    root = tree.getroot()
    volume_id = root.get("id")
    for item in root.findall('paper'): 
      printbib(item, root)
      print ()
