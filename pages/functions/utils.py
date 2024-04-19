import pandas as pd
import sqlite3 as sql
import os
from matplotlib.patches import Circle, Rectangle, Arc
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import plotly.graph_objects as go

def create_db():
    if os.path.exists(r'C:\Users\Jake\Documents\GitHub\NDA_GBB_Stats'):
        return r'C:\Users\Jake\Documents\GitHub\NDA_GBB_Stats\NDA_BB.db'
    else:
        return 'NDA_BB.db'
    
def ellipse_arc(x_center=0.0,
                 y_center=0.0, 
                 a=8.5, 
                 b=8.5, 
                 start_angle=0.0, 
                 end_angle=2 * np.pi, 
                 N=200, 
                 closed=False):
        t = np.linspace(start_angle, end_angle, N)
        x = x_center + a * np.cos(t)
        y = y_center + b * np.sin(t)
        path = f'M {x[0]}, {y[0]}'
        for k in range(1, len(t)):
            path += f'L{x[k]}, {y[k]}'
        if closed:
            path += ' Z'
        return path
    
def load_shot_chart_player(totals,
                    players_selected):
    xlocs = totals['XSPOT']
    ylocs = totals['YSPOT']
    freq_by_hex = totals['ATTEMPT']
    accs_by_hex = totals['POINTS_PER_ATTEMPT']
    spot = totals['SHOT_SPOT']
    assist_percent = totals['ASSIST_PERCENT'].round(3)
    hg_percent = totals['HG_PERCENT'].round(3)
    marker_cmin = 0.0
    marker_cmax = 2
    ticktexts = [str(marker_cmin)+'-', "", 
                 str(marker_cmax)+'+'
    ]
    hexbin_text = [
        '<i>Points Per Attempt: </i>' + str(round(accs_by_hex[i], 1)) + '<BR>'
        '<i>Attempts: </i>' + str(round(freq_by_hex[i], 2)) + '<BR>'
        '<i>Assist %: </i>' + str(round(assist_percent[i], 3)) + '<BR>'
        '<i>Heavily Guarded %: </i>' + str(round(hg_percent[i], 4))
        for i in range(len(freq_by_hex))
    ]
    str_selected = ','.join(players_selected)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xlocs, 
                             y=ylocs, 
                             mode='markers',
                             name='markers',
                             marker=dict(color=totals['POINTS_PER_ATTEMPT'],
                                         size=totals['ATTEMPT'],
                                         sizemode='area', 
                                         sizeref=2. * max(freq_by_hex) / (11. ** 3),
                                         sizemin=2.5,
                                         colorscale='RdBu',
                                         reversescale=True,
                                         colorbar=dict(thickness=15,
                                                       x=0.84,
                                                       y=0.87,
                                                       yanchor='middle',
                                                       len=0.2,
                                                       title=dict(text="<B>Points Per Attempt</B>",
                                                                  font=dict(size=11,
                                                                            color='#4d4d4d'
                                                                  ),
                                                        ),
                                                        tickvals=[marker_cmin, 
                                                                  (marker_cmin + marker_cmax) / 2, 
                                                                  marker_cmax],
                                                        ticktext=ticktexts,
                                                        tickfont=dict(size=11,
                                                                      color='#4d4d4d'
                                                        )
                                         ),
                                         cmin=marker_cmin, 
                                         cmax=marker_cmax,
                             ),
                             text=hexbin_text,
                             hoverinfo='text')
    )
    fig_height = 600 * (470 + 2 * 10) / (500 + 2 * 10)
    fig.update_layout(width=10, 
                      height=fig_height)
    fig.update_xaxes(range=[-250 - 10, 
                            250 + 10])
    fig.update_yaxes(range=[-52.5 - 10, 
                            417.5 + 10])
    threept_break_y = 0.47765084
    three_line_col = "#777777"
    main_line_col = "#777777"
    fig.update_layout(margin=dict(l=20, 
                                  r=20, 
                                  t=20, 
                                  b=20),
                      paper_bgcolor="white",
                      plot_bgcolor="white",
                      yaxis=dict(scaleanchor="x",
                                 scaleratio=1,
                                 showgrid=False,
                                 zeroline=False,
                                 showline=False,
                                 ticks='',
                                 showticklabels=False,
                                 fixedrange=True,),
                      xaxis=dict(showgrid=False,
                                 zeroline=False,
                                 showline=False,
                                 ticks='',
                                 showticklabels=False,
                                 fixedrange=True,),
                      shapes=[dict(type="rect", 
                                   x0=-250, 
                                   y0=-52.5, 
                                   x1=250, 
                                   y1=417.5,
                                   line=dict(color=main_line_col, 
                                             width=1),
                                   layer='below'),
                              dict(type="rect", 
                                   x0=-60, 
                                   y0=-52.5, 
                                   x1=60, 
                                   y1=137.5,
                                   line=dict(color=main_line_col, 
                                             width=1),
                                   layer='below'),
                              dict(type="circle", 
                                   x0=-60, 
                                   y0=77.5, 
                                   x1=60, 
                                   y1=197.5, 
                                   xref="x", 
                                   yref="y",
                                   line=dict(color=main_line_col, 
                                             width=1),
                                   layer='below'),
                              dict(type="line", 
                                   x0=-60, 
                                   y0=137.5, 
                                   x1=60, 
                                   y1=137.5,
                                   line=dict(color=main_line_col, 
                                             width=1),
                                   layer='below'),
                               dict(type="rect", 
                                    x0=-2, 
                                    y0=-7.25, 
                                    x1=2, 
                                    y1=-12.5,
                                    line=dict(color="#ec7607", 
                                              width=1),
                                    fillcolor='#ec7607',),
                               dict(type="circle", 
                                    x0=-7.5, 
                                    y0=-7.5, 
                                    x1=7.5, 
                                    y1=7.5, 
                                    xref="x", 
                                    yref="y",
                                    line=dict(color="#ec7607", 
                                              width=1),),
                              dict(type="line", 
                                   x0=-30, 
                                   y0=-12.5, 
                                   x1=30, 
                                   y1=-12.5,
                                   line=dict(color="#ec7607", 
                                             width=1),),
                              dict(type="path",
                                   path=ellipse_arc(a=40,
                                                    b=40, 
                                                    start_angle=0, 
                                                    end_angle=np.pi),
                                   line=dict(color=main_line_col, 
                                             width=1), 
                                   layer='below'),
                              dict(type="path",
                                   path=ellipse_arc(a=200.5, 
                                                    b=200.5, 
                                                    start_angle=0.0, 
                                                    end_angle=np.pi - 0.0, 
                                                    N=5000),
                                   line=dict(color=main_line_col, 
                                             width=1),
                                   layer='below'),
                              dict(type="line", 
                                   x0=-200.5, 
                                   y0=-52.5,
                                   x1=-200.5, 
                                   y1=threept_break_y,
                                   line=dict(color=three_line_col, 
                                             width=1), 
                                   layer='below'),
                              dict(type="line", 
                                   x0=200.5, 
                                   y0=-52.5, 
                                   x1=200.5, 
                                   y1=threept_break_y,
                                   line=dict(color=three_line_col, 
                                             width=1), 
                                   layer='below'),
                              dict(type="path",
                                   path=ellipse_arc(y_center=417.5, 
                                                    a=60, 
                                                    b=60, 
                                                    start_angle=-0, 
                                                    end_angle=-np.pi),
                                  line=dict(color=main_line_col, 
                                            width=1), 
                                  layer='below'),]
    )
    return fig