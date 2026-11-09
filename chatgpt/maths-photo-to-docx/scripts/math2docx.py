#!/usr/bin/env python3
"""math2docx.py: spec.txt -> .docx with native Word equations (OMML).

Usage:  python3 math2docx.py spec.txt out.docx [--no-check]

Standard library only. Builds the .docx, then checks it (structure, equation
count, text order vs the spec, and a pandoc round-trip if pandoc is installed).
Exits non-zero if the build or the check fails.
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
NS = (f'xmlns:w="{W}" xmlns:m="{M}" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')

LABEL = re.compile(r'^\(([a-z0-9]{1,4})\)\s+(.*)$')


class SpecError(Exception):
    pass


# ---------- OMML building ----------

def mrun(t):
    return ('<m:r><m:rPr><m:sty m:val="p"/></m:rPr>'
            '<m:t xml:space="preserve">' + escape(t) + '</m:t></m:r>')


def split_top(s, sep):
    """Split s on sep, ignoring separators inside nested [ ]."""
    parts, depth, cur = [], 0, ''
    for ch in s:
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    return parts


def plain_to_omml(s, ln):
    out, buf, i = [], '', 0
    while i < len(s):
        if s[i] == '^':
            if not buf:
                raise SpecError(f"line {ln}: '^' has nothing in front of it")
            base, buf = buf[-1], buf[:-1]
            if buf:
                out.append(mrun(buf))
                buf = ''
            i += 1
            if i >= len(s):
                raise SpecError(f"line {ln}: '^' has no exponent after it")
            if s[i] == '{':
                j = s.find('}', i)
                if j < 0:
                    raise SpecError(f"line {ln}: '{{' after '^' is never closed")
                exp = s[i + 1:j]
                i = j + 1
            else:
                exp = s[i]
                i += 1
            out.append('<m:sSup><m:e>' + mrun(base) + '</m:e><m:sup>' +
                       mrun(exp) + '</m:sup></m:sSup>')
        else:
            buf += s[i]
            i += 1
    if buf:
        out.append(mrun(buf))
    return ''.join(out)


def to_omml(s, ln):
    out, i = [], 0
    while i < len(s):
        if s[i] == '[':
            depth, j = 0, i
            while j < len(s):
                if s[j] == '[':
                    depth += 1
                elif s[j] == ']':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            else:
                raise SpecError(f"line {ln}: '[' is never closed")
            parts = split_top(s[i + 1:j], '|')
            if len(parts) != 2:
                raise SpecError(f"line {ln}: a fraction needs exactly one '|' inside [ ]")
            num, den = parts
            out.append('<m:f><m:fPr><m:type m:val="bar"/></m:fPr><m:num>' +
                       to_omml(num, ln) + '</m:num><m:den>' + to_omml(den, ln) +
                       '</m:den></m:f>')
            i = j + 1
        elif s[i] == ']':
            raise SpecError(f"line {ln}: ']' has no matching '['")
        else:
            j = i
            while j < len(s) and s[j] not in '[]':
                j += 1
            out.append(plain_to_omml(s[i:j], ln))
            i = j
    return ''.join(out)


# ---------- paragraphs ----------

def text_par(text, bold=False):
    rpr = '<w:rPr><w:b/></w:rPr>' if bold else ''
    ppr = '<w:pPr><w:keepNext/></w:pPr>' if bold else ''
    return ('<w:p>' + ppr + '<w:r>' + rpr + '<w:t xml:space="preserve">' + escape(text) +
            '</w:t></w:r></w:p>')


def inline_par(label, expr, ln):
    lab = '<w:r><w:t xml:space="preserve">' + escape(label) + ' </w:t></w:r>'
    return '<w:p><w:pPr><w:keepLines/></w:pPr>' + lab + '<m:oMath>' + to_omml(expr, ln) + '</m:oMath></w:p>'


def display_par(expr, ln):
    return ('<w:p><w:pPr><w:keepLines/><w:jc w:val="center"/></w:pPr>'
            '<m:oMathPara><m:oMathParaPr><m:jc m:val="centerGroup"/></m:oMathParaPr>'
            '<m:oMath>' + to_omml(expr, ln) + '</m:oMath></m:oMathPara></w:p>')


def build(lines):
    """Return (document_xml, info). info records what the check should expect."""
    body, expected_eqs, headings, spec_exprs = [], 0, [], []
    for ln, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith('%'):   # % = comment, never printed
            continue
        if line.startswith('#'):
            h = line[1:].strip()
            headings.append(h)
            body.append(text_par(h, bold=True))
        elif line.startswith('='):
            expr = line[1:].strip()
            body.append(display_par(expr, ln))
            spec_exprs.append(expr)
            expected_eqs += 1
        elif line.startswith('? '):           # ? = something to check, shown in brackets
            body.append(text_par('[Check: ' + line[2:].strip() + ']'))
        else:
            m = LABEL.match(line)
            if m:
                expr = m.group(2).strip()
                if re.search(r'[=+\-×÷^\[]', expr):   # looks like maths, not words
                    body.append(inline_par('(' + m.group(1) + ')', expr, ln))
                    spec_exprs.append(expr)
                    expected_eqs += 1
                else:
                    body.append(text_par(line))
            else:
                body.append(text_par(line))
    xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document ' + NS + '><w:body>' + ''.join(body) +
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
           '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
           'w:header="708" w:footer="708" w:gutter="0"/>'
           '</w:sectPr></w:body></w:document>')
    info = {'eqs': expected_eqs, 'exprs': spec_exprs, 'headings': headings}
    return xml, info


CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '</Relationships>')


# ---------- checks ----------

def strip_structure(expr):
    """Spec expression with layout symbols removed, to compare with the text in the file."""
    return re.sub(r'[\[\]|^{}]', '', expr)


def check_docx(path, info):
    problems = []
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    maths = root.findall(f'.//{{{M}}}oMath')
    if len(maths) != info['eqs']:
        problems.append(f"equation count is {len(maths)}, spec has {info['eqs']}")
    for el in root.iter(f'{{{M}}}f'):
        if any(not ''.join(el.itertext()).strip() for el in (el.find(f'{{{M}}}num'), el.find(f'{{{M}}}den')) if el is not None) or el.find(f'{{{M}}}num') is None or el.find(f'{{{M}}}den') is None:
            problems.append('a fraction is missing its numerator or denominator')
    for el in root.iter(f'{{{M}}}sSup'):
        if any(not ''.join(el.itertext()).strip() for el in (el.find(f'{{{M}}}e'), el.find(f'{{{M}}}sup')) if el is not None) or el.find(f'{{{M}}}e') is None or el.find(f'{{{M}}}sup') is None:
            problems.append('a superscript is missing its base or exponent')
    for got_el, expr in zip(maths, info['exprs']):
        got = ''.join(t.text or '' for t in got_el.iter(f'{{{M}}}t'))
        want = strip_structure(expr)
        if got != want:
            problems.append(f"text order differs: file '{got}' vs spec '{want}'")
    for h in sorted({h for h in info['headings'] if info['headings'].count(h) > 1}):
        problems.append(f"heading '{h}' appears more than once (duplicate page?)")
    if shutil.which('pandoc'):
        res = subprocess.run(['pandoc', '-f', 'docx', '-t', 'latex', os.path.abspath(path)],
                             capture_output=True, text=True)
        if res.returncode != 0:
            problems.append('pandoc could not open the file: ' + res.stderr.strip()[:200])
        else:
            info['pandoc_frac'] = res.stdout.count('\\frac')
            expected_fractions = len(list(root.iter(f'{{{M}}}f')))
            if info['pandoc_frac'] != expected_fractions:
                problems.append(f"pandoc read {info['pandoc_frac']} fractions, expected {expected_fractions}")
    return problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        sys.exit('usage: math2docx.py spec.txt out.docx [--no-check]')
    spec, out = args
    with open(spec, encoding='utf8') as f:
        try:
            xml, info = build(f.readlines())
        except SpecError as e:
            sys.exit('spec error, ' + str(e))
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('_rels/.rels', RELS)
        z.writestr('word/document.xml', xml)
    print('wrote', out)
    if '--no-check' in sys.argv:
        return
    problems = check_docx(out, info)
    print(f"equations: {info['eqs']}, headings: {len(info['headings'])}")
    if 'pandoc_frac' in info:
        print(f"pandoc round-trip: ok ({info['pandoc_frac']} fractions read back)")
    else:
        print('pandoc round-trip: skipped (pandoc not installed or failed)')
    if problems:
        print('CHECK FAILED:')
        for p in problems:
            print('  - ' + p)
        sys.exit(1)
    print('check: passed')


if __name__ == '__main__':
    main()
