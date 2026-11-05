from docx import Document
from pathlib import Path
from lxml import etree
def clean(e):
    if e is None: return ''
    return [(etree.QName(n).localname, {etree.QName(k).localname:v for k,v in n.attrib.items()}) for n in e.iter()]
for n in [1,3,6,8,9]:
    f=next(p for p in Path(f'{n} лабораторная').glob('*.docx') if 'отч' in p.name.lower())
    d=Document(f)
    print('\nFILE',f)
    print('SECTION',clean(d.sections[0]._sectPr))
    for i,p in enumerate(d.paragraphs[:8]):
        print(i,p.text[:65],clean(p._p.pPr),[(r.text[:16],clean(r._r.rPr)) for r in p.runs[:2]])
    print('DEFAULT',clean(d.styles.element.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}docDefaults')))
    if d.tables:
        t=d.tables[0]; print('TABLE',clean(t._tbl.tblPr),clean(t.rows[0].cells[0]._tc.tcPr))
