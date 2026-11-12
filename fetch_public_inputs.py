"""Retrieve named public inputs and retain exact URLs, dates and SHA256 hashes.

Run from the portfolio root: python shared/fetch_public_inputs.py --out work/data
Raw surveillance and sample records are deliberately excluded from the handoff ZIP.
"""
import argparse, hashlib, json, datetime, itertools
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import pandas as pd

MAP = 'https://data.malariaatlas.org/map-platform-app-backend/api/v1/trends/'
SOURCES = {
 'map_metadata': (MAP+'metadata','map_metadata.json','Release metadata'),
 'map_kenya_pfpr': (MAP+'malaria/Pf_PR-rate/admin1/mean?version=202608&iso3=KEN','kenya_pfpr.json','Modelled PfPR ages 2 to 10, not an independent observation'),
 'pf7_samples': ('https://www.malariagen.net/wp-content/uploads/2023/11/Pf7_samples.txt','Pf7_samples.txt','Historical sample metadata, not probability surveillance'),
 'pf7_resistance': ('https://www.malariagen.net/wp-content/uploads/2023/11/Pf7_inferred_resistance_status_classification.txt','Pf7_classification.txt','Inferred historical resistance classification, not treatment failures'),
 'guyana': ('https://raw.githubusercontent.com/goshgondar2018/guyana_nowcasting/32936813fcf899a7109a1d13fb50720001ec5489/data/all_regions_delays_all_inf.csv','guyana_delays.csv','Historical surveillance archive; check specimen and receipt dates'),
 'weather_guyana': ('https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=AG&longitude=-58.9&latitude=7.8&start=20120101&end=20191231&format=JSON&time-standard=UTC','guyana_point_weather.json','Retrospective gridded weather at an illustrative point, not archived forecasts'),
}

def fetch(item, folder):
    key,(url,name,note)=item
    path=folder/name
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with urlopen(Request(url,headers={'User-Agent':'MalariaResearchGroupDataAudit/1.0'}),timeout=180) as response:
        content=response.read();final_url=response.url;status=response.status
    path.write_bytes(content)
    return {'source':key,'url':url,'final_url':final_url,'retrieved_utc':now,
            'http_status':status,'bytes':len(content),
            'sha256':hashlib.sha256(content).hexdigest(),'file':name,'note':note}

def jsonstat(j):
    cats=[]
    for axis in j['id']:
        idx=j['dimension'][axis]['category']['index']
        cats.append(idx if isinstance(idx,list) else sorted(idx,key=idx.get))
    if [len(c) for c in cats]!=j['size']: raise ValueError('JSON-stat dimensions changed')
    values=j['value']; rows=[]
    for i,c in enumerate(itertools.product(*cats)):
        value=values.get(str(i)) if isinstance(values,dict) else values[i]
        rows.append(dict(zip(j['id'],c),value=value))
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='work/data')
    ap.add_argument('--sources',nargs='*',choices=list(SOURCES),default=list(SOURCES))
    args=ap.parse_args();folder=Path(args.out);folder.mkdir(parents=True,exist_ok=True)
    records=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={k:pool.submit(fetch,(k,SOURCES[k]),folder) for k in args.sources}
        for k,f in futures.items():
            try: records.append(f.result());print(k,records[-1]['bytes'])
            except Exception as ex: records.append({'source':k,'url':SOURCES[k][0],'error':str(ex)});print(k,'FAILED',ex)
    (folder/'access_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    if (folder/'kenya_pfpr.json').exists():
        j=json.loads((folder/'kenya_pfpr.json').read_text());d=jsonstat(j)
        d.to_csv(folder/'kenya_pfpr.csv',index=False)
        print('MAP schema',j['id'],j['size'],'rows',len(d))
    if (folder/'guyana_point_weather.json').exists():
        j=json.loads((folder/'guyana_point_weather.json').read_text())
        w=pd.DataFrame(j['properties']['parameter']);w.index.name='date'
        w.replace(j.get('header',{}).get('fill_value',-999),float('nan')).to_csv(folder/'guyana_point_weather.csv')
    if any('error' in r for r in records): raise SystemExit('One or more downloads failed; see manifest')
if __name__=='__main__': main()
