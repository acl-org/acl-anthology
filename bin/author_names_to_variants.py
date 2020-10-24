import lxml.etree as etree
import sys
import unicodedata

tree = etree.parse(sys.argv[1])
root = tree.getroot()
if not root.tail:
    root.tail = "\n"


def guess_script(s):
    n = len(s)
    n_latin = len([c for c in s if 'a' <= c.lower() <= 'z'])
    n_han = len([c for c in s if '\u3400' <= c <= '\u9ffc'])
    if n_latin / n > 0.5:
        return 'latn'
    if n_han / n > 0.5:
        return 'hani'


def process(names):
    scripts = [
        guess_script(''.join(part.text for part in name if part.tag in ['first', 'last']))
        for name in names
    ]
    variants = None
    if len(scripts) % 2 == 0:
        n = len(scripts) // 2
        if all(script == 'latn' for script in scripts[:n]) and all(
            script == 'hani' for script in scripts[n:]
        ):
            primaries = names[:n]
            variants = names[n:]
        elif all(script == 'hani' for script in scripts[:n]) and all(
            script == 'latn' for script in scripts[n:]
        ):
            primaries = names[n:]
            variants = names[:n]

    if variants is not None:
        for i in reversed(range(n)):
            name = variants[i]
            names.remove(name)
            name.tag = 'variant'
            name.set('script', scripts[n + i])
            primaries[i].append(name)
    else:
        print(
            f'skipping:',
            ' '.join(etree.tostring(name, encoding='unicode') for name in names),
        )


for paper in root.findall(".//paper"):
    process(list(paper.findall("author")))
for meta in root.findall(".//meta"):
    process(list(meta.findall("editor")))

tree.write(sys.argv[2], encoding='UTF-8', xml_declaration=True)
