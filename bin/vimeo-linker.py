#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019 Arne Köhn <arne@chark.eu>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Usage: vimeo_linker.py [options]

Searches for videos on the ACL vimeo channel and tries to link them
to papers.

As the vimeo api is not public, you need to copy the
vimeo_apikeys.py.dummy to vimeo_apikeys.py and fill in your API keys
obtained from vimeo.

Arguments:
  --cache-vimeo      Cache the results obtained from vimeo. For debugging.
  --cache-matchings  Cache the paper matchings. For debugging.
  --from-year=N      Papers starting at this year are considered for matching.  Newer year speeds up the matching. [default: 2013]
"""

import difflib
import vimeo
import time
import pickle
import os
import re
from anthology import Anthology
from docopt import docopt

from vimeo_apikeys import *


def checkVideo(paper):
    if not "attachment" in paper.attrib:
        return False
    for elem in paper.attrib["attachment"]:
        if elem["type"] == "video":
            return True
    return False


args = docopt(__doc__)
fromYear = int(args["--from-year"])
cacheVimeo = args["--cache-vimeo"]
cacheMatchings = args["--cache-matchings"]

v = vimeo.VimeoClient(token=personalAccessToken, key=clientId, secret=apiSecret)

allpapers = Anthology(importdir="../data/").papers

print("number of papers in anthology: ", len(allpapers))

papers = {k: v for k, v in allpapers.items() if int(v.attrib["year"]) > fromYear}
print(
    "number of papers in anthology without video after " + str(fromYear) + ": ",
    len(papers),
)


requestUrl = "/users/46432367/videos?per_page=100"
cont = True
nameUrls = {}
numRequests = 0

fetchUrls = True
if cacheVimeo and os.path.isfile("videos.pickle"):
    nameUrls = pickle.load(open("videos.pickle", "rb"))
    fetchUrls = False

while cont and fetchUrls:
    res = v.get(requestUrl)
    if res == None:
        print("Result was None; sleeping and trying again")
        time.sleep(2)
        continue
    numRequests += 1
    j = res.json()
    if not res.ok:
        print("could not fetch videos from vimeo API!")
        exit(1)
    for elem in j["data"]:
        nameUrls[elem["name"]] = elem["link"]
    requestUrl = j["paging"]["next"]
    print(requestUrl)
    cont = requestUrl != None
    # seems to be needed to not run into read timeouts.
    time.sleep(1)

if fetchUrls and cacheVimeo:
    pickle.dump(nameUrls, open("videos.pickle", "wb"))


notFounds = []
result = ""
matcher = difflib.SequenceMatcher()


def trySubstringMatch(videoName):
    for idx, p in papers.items():
        if p.is_volume:
            continue
        title = p.get_title("plain")
        if len(title) <= 20:
            continue
        if title.lower() in videoName:
            return (idx, p)
    return None


def tryMatch(name):
    matcher.set_seq1(name)
    for idx, p in papers.items():
        if p.is_volume:
            continue
        title = p.get_title("plain")
        matcher.set_seq2(title.lower())
        if (
            matcher.real_quick_ratio() > 0.8
            and matcher.quick_ratio() > 0.8
            and matcher.ratio() > 0.8
        ):
            return (idx, p)
    return None


num_elems = len(nameUrls)


id_video = []

computeMatch = True
if os.path.isfile("videos_papers.pickle") and cacheMatchings:
    id_video = pickle.load(open("videos_papers.pickle", "rb"))
    computeMatch = False


if computeMatch:
    i = 1
    for name, url in nameUrls.items():
        print(i, " of ", num_elems, end="")
        i += 1
        # clean tacl tag and author list
        if name.startswith("[TACL]"):
            name = name[6:]
        if "---" in name:
            name = name.split("---")[0]
        found = False
        # skip video names that are obviously not paper titles
        # because they don't contain spaces.
        if " " in name:
            name = name.lower()
            res = trySubstringMatch(name)
            if res == None:
                res = tryMatch(name)
            # try to remove author list appended by : or by -
            if res == None:
                if ":" in name:
                    res = tryMatch(name.rsplit(":", 1)[0])
            if res == None:
                if "-" in name:
                    res = tryMatch(name.rsplit("-", 1)[0])

            if res != None:
                (idx, p) = res
                if checkVideo(p):
                    print("video already exists, skipping ...")
                    continue
                title = p.get_title("plain")
                print("found title " + title + " for video " + name)
                result += (
                    title
                    + "\t"
                    + idx
                    + "\t"
                    + url
                    + "\t"
                    + name
                    + "\t"
                    + p.get_booktitle("plain")
                    + "\n"
                )
                id_video.append((idx, url))
            else:
                notFounds.append((name, url))
                print("no paper found for video" + name)
    f = open("/tmp/vimeo_videos.csv", "w")
    f.write("title\tACL-ID\tvideo url\tvideo name\tpaper title\n")
    f.write(result)
    f.close()
    f = open("/tmp/vimeo_not_matched.csv", "w")
    for name, url in notFounds:
        f.write(url + "\t" + name + "\n")
    f.close()

if computeMatch and cacheMatchings:
    pickle.dump(id_video, open("videos_papers.pickle", "wb"))


venues = set([x[0].split("-")[0] for x in id_video])

id_video_dict = {id: video for id, video in id_video}

paperidre = re.compile(r".*<url>(\w\d\d-\d\d\d\d)</url>")

has_video = False
idx = "notset"
for v in venues:
    with open("../data/xml/" + v + ".xml") as f:
        with open("../data/xml/" + v + ".xml.new", "w") as out:
            for l in f:
                m = paperidre.match(l)
                if m:
                    idx = m[1]  # v+"-"+m[1]
                    has_video = idx in id_video_dict
                if has_video and r"</paper>" in l:
                    out.write(
                        '      <video href="' + id_video_dict[idx] + '" tag="video"/>\n'
                    )
                    has_video = False
                out.write(l)
