"""Применение оформления отчета 9 к содержимому отчета 10 без изменения образца."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
import hashlib
from lxml import etree as E

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'10 лабораторная'
REF=ROOT/'9 лабораторная/Отчёт 9 лабораторная - Баженов Н.docx'
OUT=BASE/'Отчёт 10 лабораторная - Баженов Н.docx'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W}
def q(n): return '{'+W+'}'+n
def text(el):
    return ''.join(('\n' if n.tag==q('br') else '\t' if n.tag==q('tab') else n.text or '')
                   for n in el.xpath('.//w:t|.//w:br|.//w:tab',namespaces=NS))
def prop(el,name): return deepcopy(el.find(q(name)))
with ZipFile(REF) as z:
    parts={n:z.read(n) for n in z.namelist()}
ref=E.fromstring(parts['word/document.xml']); rb=ref.find(q('body')); rp=rb.findall(q('p'))
with ZipFile(OUT) as z: original=E.fromstring(z.read('word/document.xml'))
body=original.find(q('body')); content=list(body)
# Сохраняем содержимое до первого переформатирования для воспроизводимости.
snapshot=BASE/'проверка/content-before-format.xml'
if not snapshot.exists(): snapshot.write_bytes(E.tostring(original))
else: content=list(E.fromstring(snapshot.read_bytes()).find(q('body')))
start=next(i for i,e in enumerate(content) if text(e)=='1 Цель и задачи работы')
for el in list(rb): rb.remove(el)
def paragraph(value,template, bold=False):
    p=E.Element(q('p')); pp=prop(template,'pPr')
    if pp is not None: p.append(pp)
    run=E.SubElement(p,q('r')); rr=template.find('.//'+q('rPr'))
    if rr is not None: run.append(deepcopy(rr))
    if bold and run.find(q('rPr')) is not None and run.find(q('rPr')).find(q('b')) is None:
        E.SubElement(run.find(q('rPr')),q('b'))
    t=E.SubElement(run,q('t')); t.text=value
    return p
rb.append(paragraph('ОТЧЕТ ПО ЛАБОРАТОРНОЙ РАБОТЕ № 10',rp[0]))
meta=deepcopy(rp[1]); rb.append(meta)
# Метаданные из образца содержат только общий вариант и целевую систему.
heading=rp[2]; normal=rp[4]
ref_table=E.fromstring(parts['word/document.xml']).find('.//'+q('tbl'))
for el in content[start:]:
    if el.tag==q('sectPr'): continue
    if el.tag==q('p'):
        value=text(el)
        if not value.strip(): continue
        style=el.find('./w:pPr/w:pStyle',NS)
        is_heading=style is not None and style.get(q('val'),'').startswith('Heading')
        is_code='\n' in value and ('def ' in value or 'QUERY =' in value)
        if is_heading and value[:1].isdigit():
            num,rest=value.split(' ',1); value=f'Раздел {num}. {rest}'
        if is_code:
            # Разбиваем листинг на строки, чтобы он естественно переносился между страницами.
            for line in value.splitlines():
                p=paragraph(line or ' ',normal)
                pp=p.find(q('pPr'))
                ind=pp.find(q('ind'))
                if ind is not None: pp.remove(ind)
                spacing=pp.find(q('spacing')); spacing.set(q('line'),'240')
                r=p.find(q('r')); rr=r.find(q('rPr'))
                for n in list(rr):
                    if E.QName(n).localname in ['sz','szCs','rFonts']: rr.remove(n)
                fonts=E.SubElement(rr,q('rFonts')); fonts.set(q('ascii'),'Courier New'); fonts.set(q('hAnsi'),'Courier New')
                E.SubElement(rr,q('sz')).set(q('val'),'18')
                p.find('.//'+q('t')).set('{http://www.w3.org/XML/1998/namespace}space','preserve')
                rb.append(p)
        else:
            p=paragraph(value, heading if is_heading else normal)
            if is_heading:
                E.SubElement(p.find(q('pPr')),q('keepNext'))
            rb.append(p)
    elif el.tag==q('tbl'):
        t=deepcopy(el)
        tp=t.find(q('tblPr')); t.remove(tp); t.insert(0,prop(ref_table,'tblPr'))
        for i,row in enumerate(t.findall(q('tr'))):
            for cell in row.findall(q('tc')):
                tcpr=cell.find(q('tcPr'))
                if tcpr is not None:
                    for sh in tcpr.findall(q('shd')): tcpr.remove(sh)
                for p in cell.findall(q('p')):
                    v=text(p)
                    p.clear(); pp=prop(normal,'pPr'); p.append(pp)
                    ind=pp.find(q('ind'))
                    if ind is not None: pp.remove(ind)
                    r=E.SubElement(p,q('r')); r.append(deepcopy(normal.find('.//'+q('rPr'))))
                    if i==0: E.SubElement(r.find(q('rPr')),q('b'))
                    E.SubElement(r,q('t')).text=v
        rb.append(t)
rb.append(prop(E.fromstring(parts['word/document.xml']).find(q('body')),'sectPr'))
parts['word/document.xml']=E.tostring(ref,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(OUT,'w',ZIP_DEFLATED) as z:
    for n,data in parts.items(): z.writestr(n,data)
contract=BASE/'проверка/artifact.md'
contract.write_text(f'''Reference: {REF}\nSHA256: {hashlib.sha256(REF.read_bytes()).hexdigest()}\nPage: A4; margins top/bottom 20 mm, left 30 mm, right 15 mm.\nTypography: source direct run properties Times New Roman 14 pt; line 1.5; after 0; first line 12.5 mm.\nTitle: centered bold 14 pt; compact opening followed immediately by variant and system.\nHeadings: bold 14 pt, Раздел N.\nTables: source table properties and body typography, bold first row, no added shading.\nFlow: continuous, no separate title page or forced section page breaks.\nCode: Courier New 9 pt, single spaced, no first line indent.\nEditable: document.xml body content only. All other ZIP parts retained byte for byte.\n''',encoding='utf-8')
print('Оформление перенесено из отчета 9')
