import lxml.etree as etree
import sys
import re
import collections
import operator
import unicodedata
import yaml

threshold = 1
print_singletons = False
print_papers = True


def text(node):
    """Extract text from an XML node."""
    if node is None:
        return ""
    s = "".join(node.itertext())
    return " ".join(s.split())


def normalize(s):
    # Split before caps
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)

    # Split on punctuation
    s = "".join(" " if unicodedata.category(c).startswith("P") else c for c in s)

    # Remove accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")

    # Lowercase
    s = s.lower()

    s = " ".join(s.split())

    return s


def distance(x, y):
    """Modified Levenshtein distance, with costs for deleting a suffix or
    a whole word.  Note that this makes the distance asymmetric. This
    is because we don't want low-cost word substitutions.
    """

    c_insert = 1
    c_delete = 1
    c_subst = 1
    c_delete_suffix = 1
    c_delete_word = 1
    c_insert_space = 1
    c_delete_space = 1

    x = x.split() + [""]
    y = y.split() + [""]
    d = collections.defaultdict(lambda: float("inf"))
    d[0, 0, 0, 0] = 0
    for i in range(len(x)):
        for ii in range(len(x[i]) + 1):
            for j in range(len(y)):
                for jj in range(len(y[j]) + 1):
                    if ii > 0 and jj > 0:
                        if x[i][ii - 1] == y[j][jj - 1]:
                            d[i, ii, j, jj] = min(
                                d[i, ii, j, jj], d[i, ii - 1, j, jj - 1]
                            )  # no change
                        else:
                            d[i, ii, j, jj] = min(
                                d[i, ii, j, jj], d[i, ii - 1, j, jj - 1] + c_subst
                            )
                    if ii > 0:
                        d[i, ii, j, jj] = min(
                            d[i, ii, j, jj], d[i, ii - 1, j, jj] + c_delete
                        )
                    if jj > 0:
                        d[i, ii, j, jj] = min(
                            d[i, ii, j, jj], d[i, ii, j, jj - 1] + c_insert
                        )

                    if i > 0 and ii == 0 and j > 0 and jj == 0:
                        d[i, ii, j, jj] = min(
                            d[i, ii, j, jj], d[i - 1, len(x[i - 1]), j - 1, len(y[j - 1])]
                        )  # no change (space)
                        for kk in range(1, len(x[i - 1])):
                            d[i, ii, j, jj] = min(
                                d[i, ii, j, jj],
                                d[i - 1, kk, j - 1, len(y[j - 1])] + c_delete_suffix,
                            )

                    if i > 0 and ii == 0:
                        d[i, ii, j, jj] = min(
                            d[i, ii, j, jj], d[i - 1, 0, j, jj] + c_delete_word
                        )
                        d[i, ii, j, jj] = min(
                            d[i, ii, j, jj],
                            d[i - 1, len(x[i - 1]), j, jj] + c_delete_space,
                        )
                    if j > 0 and jj == 0:
                        d[i, ii, j, jj] = min(
                            d[i, ii, j, jj], d[i, ii, j - 1, 0] + len(y[j - 1])
                        )
                        d[i, ii, j, jj] = min(
                            d[i, ii, j, jj],
                            d[i, ii, j - 1, len(y[j - 1])] + c_insert_space,
                        )

    return d[len(x) - 1, 0, len(y) - 1, 0]


# Simple disjoint-set data structure


def union(p, x, y):
    if x not in p:
        p[x] = None
    if y not in p:
        p[y] = None
    rx = root(p, x)
    ry = root(p, y)
    if rx != ry:
        p[ry] = x  # arbitrary


def root(p, x):
    r = x
    while p[r] is not None:
        r = p[r]
    while x != r:
        temp = p[x]
        p[x] = r
        x = temp
    return r


if __name__ == "__main__":

    keys = collections.defaultdict(list)
    parent = {}
    papers = collections.defaultdict(list)
    counts = collections.Counter()

    # The idea is to generate a list of all possible rotations of all
    # names, e.g., Aravind K. Joshi becomes "aravind k joshi", "k
    # joshi aravind", "joshi aravind k". Then we sort the list and
    # compute edit distances between consecutive names on the list,
    # merging pairs whose distance is below a certain threshold.

    for filename in sys.argv[1:]:
        volume = etree.parse(filename).getroot()
        for paper in volume.findall(".//paper"):
            for person in paper.xpath("./author|./editor"):
                first = text(person.find("first"))
                last = text(person.find("last"))
                counts[first, last] += 1
                papers[first, last].append(
                    "{}-{}".format(volume.attrib["id"], paper.attrib["id"])
                )

                # Make a list of all the normalized name parts
                full = first + " " + last
                full = normalize(full)
                full = full.split()

                # Index the name by all possible rotations of the parts
                for i in range(len(full)):
                    rotated = " ".join(full[i:] + full[:i])
                    keys[rotated].append((first, last))

    for names in keys.values():
        for name in names:
            union(parent, name, names[0])

    # Just measure distance between consecutive names

    prevkey = None
    for key, names in sorted(keys.items()):
        if prevkey is not None:
            d = min(distance(prevkey, key), distance(key, prevkey))
        else:
            d = float("inf")

        if d <= threshold:
            union(parent, names[0], keys[prevkey][0])
        if prevkey is not None:
            print(
                "{}\t{} ({})\t{} ({})".format(
                    d, " ".join(keys[prevkey][0]), prevkey, " ".join(names[0]), key
                ),
                file=sys.stderr,
            )

        prevkey = key

    clusters = collections.defaultdict(list)
    for name in parent:
        clusters[root(parent, name)].append(name)

    # Re-choose canonical names, based on frequency (and then length in case of a tie)

    newclusters = {}
    for cluster, names in clusters.items():
        cname = max(names, key=lambda n: (counts[n], len(n[0]) + len(n[1])))
        newclusters[cname] = names
    clusters = newclusters

    def makename(first, last):
        d = {"first": first, "last": last}
        if print_papers:
            p = sorted(papers[first, last])
            if len(p) > 5:
                p = p[:5]
                p.append("...")
            d["papers"] = " ".join(p)
        return d

    doc = []
    for (cfirst, clast), names in sorted(
        clusters.items(), key=lambda i: (normalize(i[0][1]), normalize(i[0][0]))
    ):
        if len(names) > 1 or print_singletons:
            person = {}
            person["canonical"] = makename(cfirst, clast)
            doc.append(person)
            if len(names) > 1:
                person["variants"] = []
                for first, last in names:
                    if (first, last) == (cfirst, clast):
                        continue
                    person["variants"].append(makename(first, last))

    print(yaml.dump(doc, allow_unicode=True), end="")
