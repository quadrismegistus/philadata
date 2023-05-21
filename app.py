from philadata import *
from app_toolbox import *

PREC_ID='prec_20'


class PhilaPlots(DashFigureFactory):
    def __init__(self, df=None):
        super().__init__()
        self.df = fig_data() if df is None else df

    def filter(self, filter_data={}, with_query=False):
        if not filter_data:
            ff=self
            q=''
        else:
            df = self.df.sample(frac=1)
            ql=[]
            for k,v in filter_data.items():
                q=''
                if is_l(v):
                    q = ' | '.join(
                        f'({minv}<={k}<={maxv})'
                        for minv,maxv in iter_minmaxs(v)
                    )
                elif type(v)==str:
                    q=f'{k}=="{v}"'
                if q: ql.append(f'({q})')
            q=' & '.join(ql)
            df = df.query(q) if q else df
            ff=PhilaPlots(df=df)
        return (ff,q) if with_query else ff
    
    def plot_biplot(self, x_axis, y_axis, qual_col):
        return px.scatter(
            self.df,
            x=x_axis,
            y=y_axis,
            color=qual_col,
            template='plotly_dark',
            # trendline="ols",
            # trendline_color_override="orange",
            # trendline_scope='overall',
            # trendline_options=dict(frac=0.1)
            marginal_x='box',
            marginal_y='box'
        )
    
    def plot_parcoords(self, cols=None):
        if not cols: cols=get_nonelectoral_cols()
        fig=px.parallel_coordinates(
            self.df[cols]
        )
        # fig.update_traces(labelangle=-90)
        # fig.update_xaxes(tickangle=-90)
        # fig.update_yaxes(tickangle=-90)
        return fig
    
    def plot_map(self, color='largest_race', mapbox_style='carto-positron',**kwargs):
        fig=px.choropleth_mapbox(
            self.df,
            locations='prec_20',
            geojson=get_geojson_warddiv(),
            featureidkey='id',
            color=color,
            mapbox_style=mapbox_style,
            center=get_center_lat_lon(),
            height=800,
            zoom=9
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        return fig
    
    





class Philadata(DashComponent):
    def __init__(self):
        super().__init__()
        self.ff=PhilaPlots()


    ### INPUTS

    @cached_property
    def x_axis(self):
        return self._select_axis(
            id='x-axis', 
            placeholder='Select column for X-axis', 
            value='edu_attain'
        )
    
    @cached_property
    def y_axis(self):
        return self._select_axis(
            id='y-axis',
            placeholder='Select column for Y-axis',
            value='PRESIDENT OF THE UNITED STATES-DEM_BERNIE SANDERS'
        )
        
    @cached_property
    def qual_col(self):
        return self._select_axis(
            cols=get_qual_cols(),
            id='qual-col',
            label='Color by',
            placeholder='Select column for color',
            value='largest_race'
        )
    
    def _select_axis(self, id='axis', value='', cols=None, **kwargs):
        if cols is None: cols = get_nonelectoral_cols() + get_electoral_cols()
        options = [dict(label=x.title().replace('_',' '), value=x) for x in cols]
        return dbc.Select(
            options=options,
            value=value,
        )
    ####


    ### GRAPHS
    
    @cached_property
    def graph_map(self): return dcc.Graph(figure=self.ff.plot_map(), className='map')
    @cached_property
    def graph_parcoord(self): return dcc.Graph(figure=self.ff.plot_parcoords(), className='parcoord')
    @cached_property
    def desc_query(self): return html.Div()

    @cached_property
    def filter_data(self): return dcc.Store(id='filter_data')

    ### LAYOUT

    def layout(self):
        return dbc.Container([
            dbc.Row([
                    self.y_axis,
                    self.x_axis,
                    self.qual_col,
                    self.filter_data
            ]
            , style={'display':'none'}),
            # dbc.Row([
            dbc.Row([
                self.graph_map,
            ]),
            dbc.Row([
                self.graph_parcoord,
                self.desc_query,
            ]),
            # ])
        ])
    

    ### CALLBACKS
    def component_callbacks(self, app):
        @app.callback(    
            Output(self.filter_data, "data"),
            Input(self.graph_parcoord, 'restyleData'),
            State(self.filter_data, "data"),
        )
        def parcoord_filter_selected(restyledata, filter_data):
            if filter_data is None: filter_data = {}
            if restyledata and type(restyledata) is list:
                for d in restyledata:
                    if type(d) is dict:
                        for k,v in d.items():
                            if k.startswith('dimensions['):
                                dim_i=int(k.split('dimensions[',1)[1].split(']')[0])
                                dim = self.graph_parcoord.figure.data[0].dimensions[dim_i]
                                key = dim.label
                                filter_data[key]=v
            return filter_data

        @app.callback(    
            [
                Output(self.graph_map, "figure"),
                Output(self.desc_query, "children"),
            ],
            [
                Input(self.filter_data, "data"),
                Input(self.x_axis,'value'),
                Input(self.y_axis,'value'),
                Input(self.qual_col,'value'),
            ],
            [
                State(self.graph_map, 'figure')
            ]
        )
        def map_updated(filter_data, x_axis, y_axis, qual_col, mapfigdata):
            if not filter_data: filter_data={}
            for k,v in list(filter_data.items()):
                if v is None:
                    del filter_data[k]
            
            
            fff,qstr=self.ff.filter(filter_data, with_query=True)
            selected_ids = list(fff.df[PREC_ID])
            
            fig=go.Figure(mapfigdata)

            fig2=fff.plot_map(color=qual_col)
            fig2.layout = fig.layout
            # fig.data = fig2.data
            return fig2, qstr
            # orig_ids_map = tuple(sorted([d['id'] for d in fig.data[0].geojson['features']]))
            
            # fig.update_selections(locations=tuple(x for x in orig_ids_map if x in set(selected_ids)))

            # print(filter_data, len(self.ff.df), len(fff.df), len(selected_ids), len(fig.data[0].locations), len(fig.data[0].geojson['features']))
            
            # return fig, qstr

    

if __name__ == "__main__":
    app = DashApp(
        Philadata(), 
        # querystrings=True, 
        bootstrap=True,
    )

    print('running')
    app.run(
        host='0.0.0.0', 
        debug=True,
        port=8052,
        # threaded=True,
        # dev_tools_ui=Fas,
        use_reloader=True,
        use_debugger=True,
        reloader_interval=1,
        reloader_type='watchdog'
    )


