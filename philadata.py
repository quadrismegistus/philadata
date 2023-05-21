## Constants
TITLE = 'Philadata'

## Sys imports
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime as dt
import os,sys,copy,time
import requests
import json

## Non-sys imports
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from functools import lru_cache, cached_property


## Setup plotly
# Plotly mapbox public token
mapbox_access_token = open(os.path.expanduser('~/.mapbox_token')).read()
px.set_mapbox_access_token(mapbox_access_token)
px.defaults.template='plotly_dark'


path_philadata_code=os.path.abspath(os.path.dirname(__file__))
path_philadata_data=os.path.join(path_philadata_code,'data')
if not os.path.exists(path_philadata_data): os.makedirs(path_philadata_data)


URLS = {
    'ward_divisions':'https://data-phl.opendata.arcgis.com/datasets/160a3665943d4864806d7b1399029a04_0.geojson'
}



#############
# DATA SETUP #
#############

@lru_cache(maxsize=None)
def precinct_data():
    df=pd.read_csv(os.path.join(os.path.dirname(__file__), 'prec_results_demos.csv'))
    df['prec_20'] = df['prec_20'].apply(lambda x: f'{int(x):04}')
    df['ward'] = df['prec_20'].apply(lambda x: x[:2])
    df['prec'] = df['prec_20'].apply(lambda x: x[2:])
    df=df.set_index(['ward','prec']).sort_index()
    df=df[[c for c in df if not (c[0]=='B' and c[1].isdigit())]]
    return df


def corr_data(cols=[]):
    df=precinct_data()
    if cols: df=df[[c for c in df if c in set(cols)]]
    df=df.select_dtypes('number')
    df=df.corr()
    return df


@lru_cache(maxsize=None)
def fig_data():
    df=precinct_data().reset_index()
    for col in get_qual_cols():
        df[col]=df[col].apply(str)
    return df





def get_electoral_cols():
    return [c for c in precinct_data() if c[0]==c[0].upper()]

def get_nonelectoral_cols(quant=None):
    return [
        c 
        for c in precinct_data()
        if c[0]==c[0].lower() and c.split('_')[0] not in {'clust','prec','total'}
        and c+'_share' not in set(precinct_data().columns)
        and (not quant or c not in set(get_qual_cols()))
    ]

@lru_cache
def get_qual_cols():
    o=set(precinct_data().select_dtypes(exclude='number').columns)
    return sorted(list(o))


def is_l(x): return type(x) in {list,tuple}
def iter_minmaxs(l):
    if is_l(l):
        for x in l:
            if is_l(x):
                if len(x)==2 and not is_l(x[0]) and not is_l(x[1]):
                    yield x
                else:
                    yield from iter_minmaxs(x)




def get_geojson_warddiv(fn='ward_divisions.geojson', force=False):
    fn=os.path.join(path_philadata_data, fn) if not os.path.isabs(fn) else fn
    url=URLS.get('ward_divisions')
    if force or not os.path.exists(fn):
        data = requests.get(url)
        with open(fn,'wb') as of: 
            of.write(data.content)

    # load        
    with open(fn) as f:
        jsond=json.load(f)
        
    # anno
    for d in jsond['features']:
        d['id'] = str(d['properties']['DIVISION_NUM'])
    
    return jsond


@lru_cache(maxsize=None)
def get_center_lat_lon():
    xl=[]
    yl=[]
    for d in get_geojson_warddiv()['features']:
        for x,y in iter_minmaxs(d['geometry']['coordinates']):
            xl.append(x)
            yl.append(y)
    center_lon,center_lat=np.median(xl),np.median(yl)
    return {'lat':center_lat, 'lon':center_lon}