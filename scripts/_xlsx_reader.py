import zipfile, re, sys
from xml.etree import ElementTree as ET
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

class WB:
    def __init__(self, path):
        self.z=zipfile.ZipFile(path)
        self.shared=self._shared()
        self.sheets=self._sheets()
    def _shared(self):
        try: x=self.z.read('xl/sharedStrings.xml')
        except KeyError: return []
        out=[]
        for si in ET.fromstring(x).findall('m:si',NS):
            out.append(''.join(t.text or '' for t in si.iter('{%s}t'%NS['m'])))
        return out
    def _sheets(self):
        wb=ET.fromstring(self.z.read('xl/workbook.xml'))
        rels=ET.fromstring(self.z.read('xl/_rels/workbook.xml.rels'))
        rmap={r.get('Id'):r.get('Target') for r in rels}
        out=[]
        for s in wb.find('m:sheets',NS):
            rid=s.get('{%s}id'%NS['r'])
            t=rmap.get(rid,'')
            if not t.startswith('xl/'): t='xl/'+t.lstrip('/')
            out.append((s.get('name'), t, s.get('state','visible')))
        return out
    def rows(self, target, limit=None):
        try: data=self.z.read(target)
        except KeyError: return
        n=0
        for _,el in ET.iterparse(__import__('io').BytesIO(data)):
            if el.tag=='{%s}row'%NS['m']:
                cells={}
                for c in el.findall('m:c',NS):
                    ref=c.get('r') or ''
                    col=re.match(r'[A-Z]+',ref).group(0) if re.match(r'[A-Z]+',ref) else ''
                    t=c.get('t'); v=c.find('m:v',NS); isel=c.find('m:is',NS)
                    if isel is not None:
                        val=''.join(x.text or '' for x in isel.iter('{%s}t'%NS['m']))
                    elif v is None: val=None
                    elif t=='s': val=self.shared[int(v.text)] if v.text and int(v.text)<len(self.shared) else None
                    else: val=v.text
                    if val not in (None,''): cells[col]=val
                yield cells
                el.clear(); n+=1
                if limit and n>=limit: return

if __name__=='__main__':
    for p in sys.argv[1:]:
        print('='*80); print(p.split('/')[-1]); print('='*80)
        w=WB(p)
        for name,target,state in w.sheets:
            cnt=sum(1 for _ in w.rows(target))
            print(f"  [{state:8}] {name!r:55} rows={cnt}")
