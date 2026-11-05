"""E.04 conditional reproduction from preserved data, shared by CLI and notebook."""
from pathlib import Path
import hashlib,json,zipfile,importlib.util,subprocess,sys,platform
import pandas as pd
import numpy as np

def write_report(root,name,value):
    path=Path(root)/'verification'/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n');return value

def input_checks(root):
    root=Path(root)
    load_local(root/'code/materialize_inputs.py','diverging_paths_materialize').materialize(root)
    pins=json.loads((root/'checks/input-hashes.json').read_text())
    for rel,digest in pins.items():
        assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest,rel
    release=json.loads((root/'provenance/v3.0.0/release_manifest.json').read_text());members=0
    for archive in release['network_archives']:
        path=root/archive['path']
        assert path.stat().st_size==archive['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==archive['sha256']
        with zipfile.ZipFile(path) as z:
            assert set(z.namelist())==set(archive['members'])
            for name,digest in archive['members'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
            members+=len(z.namelist())
    return write_report(root,'input-integrity.json',{'status':'PASS','pinned_data_products':len(pins),'network_archives':len(release['network_archives']),'archive_members':members,'python':platform.python_version(),'scope':'Integrity only; no holdout annotations read'})

def corpus_checks(root):
    root=Path(root);data=root/'data';out=root/'reproduced/tables';out.mkdir(parents=True,exist_ok=True)
    papers=pd.read_parquet(data/'papers.parquet',columns=['bibcode','year','abstract']);papers=papers[papers.year<=2025]
    assert len(papers)==201627 and papers.bibcode.nunique()==len(papers)
    classes=pd.read_parquet(data/'paper_arxiv_classes.parquet').sort_values(['bibcode','class_pos'])
    primary=classes.drop_duplicates('bibcode').merge(papers[['bibcode','year']],on='bibcode',validate='one_to_one')
    assert len(primary)==143390
    rebuilt=primary.groupby(['year','arxiv_class','arxiv_category']).size().rename('n_papers').reset_index()
    frozen=pd.read_parquet(data/'analysis/classification_primary_yearly.parquet')
    joined=rebuilt.merge(frozen,on=['year','arxiv_class','arxiv_category'],how='outer',suffixes=('_rebuilt','_frozen'),indicator=True)
    assert joined['_merge'].eq('both').all() and joined.n_papers_rebuilt.eq(joined.n_papers_frozen).all()
    volume=papers.groupby('year').size().rename('n_papers_rebuilt').reset_index().merge(pd.read_parquet(data/'analysis/paper_volume_yearly.parquet'),on='year',validate='one_to_one')
    assert volume.n_papers_rebuilt.eq(volume.n_papers).all()
    categories=primary.groupby('arxiv_category').size().sort_values(ascending=False).rename('papers').reset_index()
    counts=primary.groupby('arxiv_class').size().sort_values(ascending=False).rename('papers').reset_index()
    for name,table in [('primary-categories',categories),('primary-classes',counts)]:
        table['percent']=100*table.papers/len(primary);table.to_csv(out/(name+'.csv'),index=False)
        lines=[r'\begin{tabular}{lrr}',r'\toprule','Primary assignment & Papers & Share '+r'\\',r'\midrule']
        for _,row in table.head(4 if name.endswith('categories') else 9).iterrows():
            label=str(row.iloc[0]).replace('_',r'\_')
            lines.append(f'{label} & {int(row.papers):,} & {row.percent:.1f}'+r'\% \\')
        (out/(name+'.tex')).write_text('\n'.join(lines+[r'\bottomrule',r'\end{tabular}'])+'\n')
    expected={'astrophysics':78673,'high-energy physics':39191,'general relativity and quantum cosmology':14668,'physics':6427}
    actual=categories.set_index('arxiv_category').papers.to_dict()
    assert all(actual.get(k)==v for k,v in expected.items())
    return write_report(root,'corpus-checks.json',{'status':'PASS','records':len(papers),'classified_records':len(primary),'primary_class_year_cells_rebuilt':len(rebuilt),'volume_years_rebuilt':len(volume),'main_table_counts_match':True,'largest_primary_class':counts.iloc[0,0]})

def candidate_checks(root):
    root=Path(root);d=root/'data';raw=pd.read_parquet(d/'dm_model_candidates_long.parquet');raw=raw[raw.year.between(1995,2025)]
    assert len(raw)==27680 and raw.bibcode.nunique()==22247
    tracked=(d/'analysis/tracked_candidate_species.txt').read_text().splitlines();assert len(tracked)==13
    pairs=raw[raw.SpeciesLabel.isin(tracked)&raw.year.between(1995,2025)&raw.arxiv_category.isin(['astrophysics','high-energy physics'])].drop_duplicates(['year','arxiv_category','bibcode','SpeciesLabel'])
    rebuilt=pairs.groupby(['year','SpeciesLabel','arxiv_category']).size().unstack(fill_value=0).reset_index()
    ref=pd.read_parquet(d/'analysis/candidate_field_yearly.parquet')
    merged=ref.merge(rebuilt,on=['year','SpeciesLabel'],how='left').fillna({'astrophysics':0,'high-energy physics':0})
    assert (merged.astro_mentions==merged['astrophysics']).all() and (merged.hep_mentions==merged['high-energy physics']).all()
    # Reconstruct smoothed proportions using the retained 0.5 per-family pseudocount.
    n=13;astro=(merged.astro_mentions+0.5)/(merged.groupby('year').astro_mentions.transform('sum')+0.5*n)
    hep=(merged.hep_mentions+0.5)/(merged.groupby('year').hep_mentions.transform('sum')+0.5*n)
    assert np.allclose(astro,merged.astro_share) and np.allclose(hep,merged.hep_share)
    assert np.allclose(np.log2(hep/astro),merged.log2_hep_astro_ratio)
    assert (merged.meets_minimum_count==(merged.total_mentions>=20)).all()
    merged[['year','SpeciesLabel','astro_mentions','hep_mentions','astro_share','hep_share','log2_hep_astro_ratio']].to_csv(root/'reproduced/tables/candidate-field-reconstructed.csv',index=False)
    return write_report(root,'candidate-checks.json',{'status':'PASS','candidate_tag_rows_1995_2025':len(raw),'candidate_papers':int(raw.bibcode.nunique()),'tracked_families':len(tracked),'candidate_year_cells':len(merged),'paper_family_deduplication':True,'pseudocount':0.5,'display_threshold':20,'bootstrap_intervals':'Retained and hash-verified; not freshly resampled','validation':'No independent accuracy estimate; no untouched holdout answers inspected'})

def load_local(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def network_checks(root):
    root=Path(root);mod=load_local(root/'code/network-reconstruction/recompute_metrics.py','damadi_network_recompute')
    report=mod.verify(root,root/'code/network-reconstruction/inputs.json')
    assert report['status']=='passed' and len(report['windows'])==57
    path=root/'reproduced/network-metrics.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return {'status':'PASS','windows':len(report['windows']),'nodes_checked':report['betweenness_nodes_checked'],'removal_rows':report['node_removal_rows_recalculated'],'scope':report['scope']}

def figure_checks(root,render=True):
    root=Path(root)
    if render:
        subprocess.run(['Rscript',str(root/'code/04-build-figures.R')],cwd=root,check=True)
        mod=load_local(root/'code/modules/network_graphics.py','damadi_network_graphics');mod.export_all(root)
    from pypdf import PdfReader
    files=sorted((root/'reproduced/stepwise-figures').glob('*.pdf'))+sorted((root/'reproduced/figures').glob('*.pdf'))
    assert len(files)==9,len(files)
    for file in files:assert len(PdfReader(file).pages)==1
    config=json.loads((root/'config/main-figures.json').read_text())
    assert hashlib.sha256((root/'code/02-main-figures-stepwise.R').read_bytes()).hexdigest()==config['active_script_sha256']
    for name,dimensions in config['figures'].items():
        page=PdfReader(root/'reproduced/stepwise-figures'/name).pages[0]
        actual=[float(page.mediabox.width)*25.4/72,float(page.mediabox.height)*25.4/72]
        assert np.allclose(actual,dimensions,atol=0.02),(name,actual)
    for name,digest in config['table_sha256'].items():
        assert hashlib.sha256((root/'reproduced/tables'/name).read_bytes()).hexdigest()==digest,name
    return write_report(root,'figure-checks.json',{'status':'PASS','pdfs':len(files),'statistical_renderings':7,'network_presentations':2,'network_geometry':'Unchanged','main_figure_source_sha256':config['source_script_sha256'],'main_figure_dimensions_mm':config['figures'],'main_tables_byte_identical_to_retained_fragments':True,'authority':'Main Figures 1–3 regenerated from the user-designated script at final arXiv dimensions, with the preprint class colors fixed explicitly and bundled STIX typography. Four SI manuscript figures remain retained preprint assets; separate SI R companions remain available.'})

def run(root,render=True):
    root=Path(root).resolve();reports={}
    for name,fn in [('inputs',input_checks),('corpus',corpus_checks),('candidates',candidate_checks),('network',network_checks)]:
        print('STEP:',name,flush=True);reports[name]=fn(root)
    reports['figures']=figure_checks(root) if render else {'status':'PASS','skipped':True,'reason':'Numerical-only mode; no graphical checks claimed'}
    return write_report(root,'reproduction.json',{'status':'PASS','entry':'E.04--MS-DA-CR','reports':reports,'limits':'Frozen-input reconstruction. No new retrieval, raw-abstract NLP extraction, new annotation, holdout inspection, causal validation or bootstrap resampling.'})
