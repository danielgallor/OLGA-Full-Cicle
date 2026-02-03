# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 13:50:38 2020

@author: agan.balangalibun
"""

import plotly
import plotly.graph_objects as go
import pandas as pd
import json

############################# INPUTS ################################
with open('main.json', 'r') as file:
        readjson = json.load(file)


filepath = readjson.get("file_path")
study_name = readjson.get("dataframe_read_file")
output_filepath = readjson.get("output_filepath")
output_name = readjson.get("output_name")


df = pd.read_csv(filepath + '\\'+ study_name+'.csv')

plot = plotly.offline.plot


fig = go.Figure(data=
    go.Parcoords(
        line = dict(color = df['line Size (nominal Bore)Inch'],
                                        colorscale = [[0,'lightseagreen'],[1,'orange']],
                                        cmin= 10,
                                        cmax = 12,
                                        ),
        rangefont = dict(color = 'white',
                         size = 1,
                         family = 'Arial'),
        dimensions = list([
            dict(
                 label = 'line Size (Inch)',
                 # range = [],
                 # constraintrange = [],
                 range = [df['line Size (nominal Bore)Inch'].min() -(df['line Size (nominal Bore)Inch'].max() * 0.1),
                         df['line Size (nominal Bore)Inch'].max() * 1.1],
                 constraintrange = [df['line Size (nominal Bore)Inch'].min() -(df['line Size (nominal Bore)Inch'].max() * 0.1),
                                   df['line Size (nominal Bore)Inch'].max() * 1.1],
                 values = df['line Size (nominal Bore)Inch']),
            dict(
                label = 'Gas Production Rate (MMscfd)',
                # range =[,],
                 # constraintrange = [,],
                range = [df['Gas Production Rate (MMscfd)'].min()-(df['Gas Production Rate (MMscfd)'].max() * 0.1),
                         df['Gas Production Rate (MMscfd)'].max() * 1.1],
                constraintrange = [df['Gas Production Rate (MMscfd)'].min()-(df['Gas Production Rate (MMscfd)'].max() * 0.1),
                                   df['Gas Production Rate (MMscfd)'].max() * 1.1],
                values = df['Gas Production Rate (MMscfd)']),
            dict(
                 label = 'CGR (stbmmscf)',
                 # range =[,],
                 # constraintrange = [,],
                 range = [df['CGR (stbmmscf)'].min() -(df['CGR (stbmmscf)'].max() * 0.1),
                         df['CGR (stbmmscf)'].max() * 1.1],
                 constraintrange = [df['CGR (stbmmscf)'].min() -(df['CGR (stbmmscf)'].max() * 0.1),
                                   df['CGR (stbmmscf)'].max() * 1.1],
                 values = df['CGR (stbmmscf)']),
            dict(
                 label = 'WGR (stb/mmscf)',
                 # range =[,],
                 # constraintrange = [,],
                 range = [df['WGR (stbmmscf)'].min() -(df['WGR (stbmmscf)'].max() * 0.1),
                         df['WGR (stbmmscf)'].max() * 1.1],
                 constraintrange = [df['WGR (stbmmscf)'].min() -(df['WGR (stbmmscf)'].max() * 0.1),
                                   df['WGR (stbmmscf)'].max() * 1.1],
                 values = df['WGR (stbmmscf)']),
            dict(
                 label = 'Downstream Presssure (barg)',
                 # range =[,],
                 # constraintrange = [,],
                 range = [df['Downstream Presssure (barg)'].min() -(df['Downstream Presssure (barg)'].max() * 0.1),
                         df['Downstream Presssure (barg)'].max() * 1.1],
                 constraintrange = [df['Downstream Presssure (barg)'].min() -(df['Downstream Presssure (barg)'].max() * 0.1),
                                   df['Downstream Presssure (barg)'].max() * 1.1],
                 values = df['Downstream Presssure (barg)']),
              
            dict(
                 label = 'WHP (barg)',
                 # range =[,],
                 # constraintrange = [,],
                 range = [df['WHP (barg)'].min() -(df['WHP (barg)'].max() * 0.1),
                         df['WHP (barg)'].max() * 1.1],
                 constraintrange = [df['WHP (barg)'].min() -(df['WHP (barg)'].max() * 0.1),
                                   df['WHP (barg)'].max() * 1.1],
                 values = df['WHP (barg)']),
            
            dict(
                 label = 'Max Temperature (degC)',
                 # range =[,],
                 # constraintrange = [,],
                 range = [df['Max Temperature (degC)'].min() -(df['Max Temperature (degC)'].max() * 0.1),
                         df['Max Temperature (degC)'].max() * 1.1],
                 constraintrange = [df['Max Temperature (degC)'].min() -(df['Max Temperature (degC)'].max() * 0.1),
                                   df['Max Temperature (degC)'].max() * 1.1],
                 values = df['Max Temperature (degC)']),
            
        ])
             
    )             
)
               
fig.show()

plot(fig,auto_open = True,filename = filepath + '\\'+output_name+'.html',)
