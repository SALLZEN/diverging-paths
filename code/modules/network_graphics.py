"""Retype retained network labels in STIX while preserving every non-text operation."""
from pathlib import Path
import io,json,math,hashlib
import fitz
from pypdf import PdfReader,PdfWriter
from pypdf.generic import ContentStream,NameObject,DecodedStreamObject
TEXT_OPS={b'BT',b'ET',b'Tf',b'Tj',b'TJ',b"'",b'"',b'Td',b'TD',b'T*',b'Tm',b'Tz',b'Tr',b'Ts',b'Tc',b'Tw',b'TL'}

def normalize_one(source,destination,font_dir):
    source=Path(source);destination=Path(destination);font_dir=Path(font_dir)
    original=fitz.open(source);page=original[0]
    assert len(original)==1 and page.rotation==0
    overlays=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            assert abs(line['dir'][1])<1e-8 and line['dir'][0]>0
            for span in line['spans']:
                font=span['font']
                face='math' if 'Math' in font else 'italic' if 'Italic' in font else 'medium' if 'IBM' in font or 'Bold' in font or 'Medium' in font else 'regular'
                overlays.append({'text':span['text'],'origin':span['origin'],'bbox':span['bbox'],'size':span['size'],'color':span['color'],'face':face,'source_font':font})
    reader=PdfReader(source);writer=PdfWriter();writer.clone_document_from_reader(reader);fingerprints=[];visited=set()
    def clean(stream,resources,label):
        key=id(stream)
        if key in visited:return
        visited.add(key)
        content=ContentStream(stream,writer);before=[];after=[];kept=[]
        for operands,op in content.operations:
            if op==b'Tr':assert float(operands[0])<4,'Text clipping requires explicit treatment'
            if op not in TEXT_OPS:before.append((repr(operands),op.decode('latin1')));kept.append((operands,op));after.append((repr(operands),op.decode('latin1')))
        assert before==after
        fingerprints.append({'stream':label,'nontext_operations':len(before),'sha256':hashlib.sha256(repr(before).encode()).hexdigest()})
        content.operations=kept;stream.set_data(content.get_data())
        if '/Font' in resources:del resources['/Font']
        for name,value in resources.get('/XObject',{}).items():
            obj=value.get_object()
            if obj.get('/Subtype')=='/Form':clean(obj,obj.get('/Resources',resources).get_object(),label+'/'+str(name))
    pdfpage=writer.pages[0]
    # Flatten the page content array into one stream without changing drawing operations.
    contents=ContentStream(pdfpage.get_contents(),writer);pdfpage[NameObject('/Contents')]=writer._add_object(contents)
    clean(contents,pdfpage['/Resources'].get_object(),'page')
    overlay=fitz.open();newpage=overlay.new_page(width=page.rect.width,height=page.rect.height)
    faces={'regular':'STIXTwoText-Regular.ttf','italic':'STIXTwoText-Italic.ttf','medium':'STIXTwoText-Medium.ttf','math':'STIXTwoMath-Regular.otf'}
    fonts={k:fitz.Font(fontfile=str(font_dir/v)) for k,v in faces.items()}
    for k,v in faces.items():newpage.insert_font(fontname='DAMADI'+k,fontfile=str(font_dir/v))
    for span in overlays:
        text=span['text'];face=span['face'];font=fonts[face]
        assert all(c.isspace() or font.has_glyph(ord(c)) for c in text),(text,face)
        width=font.text_length(text,fontsize=span['size']);source_width=span['bbox'][2]-span['bbox'][0]
        factor=source_width/width if width>0 else 1
        origin=fitz.Point(span['origin']);rgb=fitz.sRGB_to_pdf(span['color'])
        newpage.insert_text(origin,text,fontsize=span['size'],fontname='DAMADI'+face,color=rgb,morph=(origin,fitz.Matrix(factor,1)))
        span['horizontal_scale']=factor
    overlay_writer=PdfWriter();overlay_writer.clone_document_from_reader(PdfReader(io.BytesIO(overlay.tobytes())))
    # MuPDF's CFF insertion needs an explicit UTF-16 mapping for non-BMP math letters.
    math_chars=sorted({c for span in overlays if span['face']=='math' for c in span['text']})
    if math_chars:
        pairs=[f'<{fonts["math"].has_glyph(ord(c)):04X}> <{c.encode("utf-16-be").hex().upper()}>' for c in math_chars]
        cmap='/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /DAMADI-Math-Unicode def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n'+str(len(pairs))+' beginbfchar\n'+'\n'.join(pairs)+'\nendbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n'
        stream=DecodedStreamObject();stream.set_data(cmap.encode())
        overlay_writer.pages[0]['/Resources']['/Font']['/DAMADImath'].get_object()[NameObject('/ToUnicode')]=overlay_writer._add_object(stream)
    pdfpage.merge_page(overlay_writer.pages[0])
    writer.add_metadata({'/Title':'DAMADI STIX presentation of retained network figure','/Author':'Simon Allzén','/Subject':'Original graph geometry and source label positions retained; STIX typography only'})
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('wb') as output:writer.write(output)
    rendered=fitz.open(destination)
    expected=''.join(x['text'] for x in overlays)
    # Verify every source label's characters remain in the presentation text layer.
    actual=rendered[0].get_text()
    from collections import Counter
    assert Counter(c for c in expected if not c.isspace())==Counter(c for c in actual if not c.isspace())
    return {'source':source.name,'pdf':destination.name,'label_spans':overlays,'nontext_stream_fingerprints':fingerprints,'all_nontext_operations_unchanged':True,'source_label_characters_retained':True,'font_sizes_and_origins_retained':True,'width_mm':page.rect.width*25.4/72,'height_mm':page.rect.height*25.4/72}

def export_all(root):
    root=Path(root);records=[]
    for old,new in [('graph-01.pdf','fig-cross-field-brokerage.pdf'),('graph_removal.pdf','fig-si-node-removal.pdf')]:
        records.append(normalize_one(root/'resources/retained-figures'/old,root/'reproduced/figures'/new,root/'resources/fonts'))
    (root/'verification/network-figure-typography.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    return records

if __name__=='__main__':
    import sys
    export_all(Path(sys.argv[1]))
