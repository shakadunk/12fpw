#!/usr/bin/env python3
"""Turn a Mac .textClipping (as sent from Finder) into the text.txt that scripts/add-post.mjs expects.

  python3 scripts/clipping_to_text.py "path/to/clipping.textClipping" > text.txt

 - paragraphs are separated by a blank line; the sign-off ("In motion," / "SD") stays as two lines in the last paragraph
 - an all-italic paragraph is wrapped in asterisks, which the site shows as the grey italic "preface"
 - a leading "Week N" line is dropped (the site adds its own heading)
 - hyperlinks are kept as [words](https://address), which the site shows underlined and slightly heavier
"""
import plistlib, re, sys, html

def build(path):
    d = plistlib.load(open(path, 'rb'))['UTI-Data']
    arc = plistlib.loads(d['com.apple.webarchive'])
    h = arc['WebMainResource']['WebResourceData'].decode('utf8')
    out = []
    chunks = [m.group(1) for m in re.finditer(r'<p\b[^>]*>(.*?)</p>', h, re.S)]
    if not chunks:                       # a short clipping can be a bare <span> with no <p> tags: use everything after <head>
        body = re.sub(r'(?is)<!DOCTYPE[^>]*>|<head>.*?</head>', '', h)
        chunks = [body]
    for chunk in chunks:
        inner = chunk.strip()
        ital = inner.startswith('<em>') and inner.endswith('</em>')
        inner = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', lambda a: '[' + re.sub(r'<[^>]+>', '', a.group(2)) + '](' + a.group(1) + ')', inner, flags=re.S)
        t = re.sub(r'<br\s*/?>', '\n', inner)
        t = re.sub(r'<[^>]+>', '', t)
        t = html.unescape(t).replace(' ', '\n').replace('\xa0', ' ')
        t = '\n'.join(l.strip() for l in t.split('\n')).strip()
        if not t or re.fullmatch(r'Week\s*\d+\.?', t, re.I):
            continue
        out.append('*' + t + '*' if ital else t)
    return '\n\n'.join(out) + '\n'

if __name__ == '__main__':
    sys.stdout.write(build(sys.argv[1]))
