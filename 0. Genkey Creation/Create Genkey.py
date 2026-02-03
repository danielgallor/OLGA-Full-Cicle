import pandas as pd
import json
import re


with open('main.json', 'r') as file:
        readjson = json.load(file)


working_location = readjson.get("Working Location")
working_file = working_location + "\\OLGA Standard Modelling Basis.xlsm"
material_excel_tab = "Walls Construction"
well_material_excel_tab = "Well Walls Construction"
fluid_excel_tab = "Fluid"
geometry_excel_tab =  "Geometry"
boundary_excel_tab = "Boundary Conditions"
boundary_variables_tab = "OUTPUT Variables Boundary"
volume_variables_tab = "OUTPUT Variables Volume"
OLGA_genkey = working_location + "\\Python\\Base.genkey"



### 1- READ THE WALLS CONTRUCTION TAB IN THE EXCEL SHEET, COPY ALL THE AVAILABLE DATA ON WALLS AND MATERIALS AND SAVES IT ###

pipe_materials = pd.read_excel(working_file, material_excel_tab, engine = "openpyxl", usecols = [17], skiprows = 2, header=None)
pipe_materials = pipe_materials.dropna()
pipe_materials = pipe_materials.iloc[:, 0]

well_materials = pd.read_excel(working_file, well_material_excel_tab, engine = "openpyxl", usecols = [17], skiprows = 2, header=None)
well_materials = well_materials.dropna()
well_materials = well_materials.iloc[:, 0]


pipe_walls =  pd.read_excel(working_file, material_excel_tab, engine = "openpyxl", usecols = [26], skiprows = 2, header=None)
pipe_walls = pipe_walls.dropna()
pipe_walls = pipe_walls.iloc[:,0]


well_walls =  pd.read_excel(working_file, well_material_excel_tab, engine = "openpyxl", usecols = [26], skiprows = 2, header=None)
well_walls = well_walls.dropna()
well_walls = well_walls.iloc[:,0]



materials_walls = pd.concat([pipe_materials, pipe_walls, well_materials, well_walls], ignore_index=True)
materials_to_genkey = materials_walls.to_list()


        
### 2- READ THE FLUUID TAB AND STORE THE MF FILE LOCATION ###

MF_path = pd.read_excel(working_file, fluid_excel_tab, engine = "openpyxl")
MF_path_to_genkey = MF_path.columns[1]
fluid_name = MF_path.iloc[0,1]



### 3- READ THE GEOMETRY TAB AND STORE THE ELEVATION / LENGTH PROFILE ###
geo_tab = pd.read_excel(working_file, geometry_excel_tab, engine = "openpyxl", header = None)
branch_name = geo_tab.iloc[0,1]
first_pipe_name = geo_tab.iloc[3,3]


geometry = pd.read_excel(working_file, geometry_excel_tab, engine = "openpyxl", usecols=[11], skiprows=1)
geometry = geometry.dropna()
geometry = geometry.iloc[1:, 0]


geometry_to_genkey = []


for item in geometry: 
    geometry_to_genkey.append(item)


### 4- READ THE BOUNDARY CONDITIONS TAB AND STORE NODE, PARAMETER, VALUE AND UNIT ###
boundary_inlet = pd.read_excel(working_file, boundary_excel_tab, engine = "openpyxl", usecols=[0,1,2,3], skiprows=12)

boundary_source = pd.read_excel(working_file, boundary_excel_tab, engine = "openpyxl", usecols=[6,7,8,9,10], skiprows=12)
boundary_source_changes = {para:valueunit for para, valueunit  in zip(boundary_source["PARAMETER.1"],boundary_source["VALUE.1"].astype(str)+" "+boundary_source["UNIT.1"])}

boundary_outlet = pd.read_excel(working_file, boundary_excel_tab, engine = "openpyxl", usecols=[13,14,15,16], skiprows=12).dropna()
boundary_outlet_changes = {para:valueunit for para, valueunit  in zip(boundary_outlet["PARAMETER.2"],boundary_outlet["VALUE.2"].astype(str)+" "+boundary_outlet["UNIT.2"])}


###  READ OUTPUT VARIABLES TAB AND EXTRACT SELECTED VARIABLES

temp_trend_boundary_outputs = pd.read_excel(working_file, boundary_variables_tab, engine = "openpyxl", usecols=[0,1,2,3,4,5], skiprows=3).dropna()
trend_boundary_outputs = temp_trend_boundary_outputs[temp_trend_boundary_outputs["Add to Model"].astype(float).eq(1.0)].copy()
trend_boundary_outputs_to_genkey = {}

for pipe,sections,variable in zip(trend_boundary_outputs["Pipe"], trend_boundary_outputs["Section"], trend_boundary_outputs["Output"]):
    if isinstance(sections, float):
        sections = int(sections)

    pipesection = [ f"{pipe} {str(sections)}"]

    for pipesec in pipesection:
        if pipesec not in trend_boundary_outputs_to_genkey or trend_boundary_outputs_to_genkey[pipesec] is None:
            trend_boundary_outputs_to_genkey[pipesec] = [variable]
        else:
           trend_boundary_outputs_to_genkey[pipesec].append(variable)
        
temp_profile_boundary_outputs = pd.read_excel(working_file, boundary_variables_tab, engine = "openpyxl", usecols=[7,8,9,10,11], skiprows=3).dropna()
profile_boundary_outputs = temp_profile_boundary_outputs[temp_profile_boundary_outputs["Add to Model.1"].astype(float).eq(1.0)].copy()

profile_boundary_outputs_to_genkey = {}

for branch in profile_boundary_outputs["Branch Name"].unique():
    for variable in profile_boundary_outputs["Output.1"]:
        if branch not in profile_boundary_outputs_to_genkey or profile_boundary_outputs_to_genkey[branch] is None:
            profile_boundary_outputs_to_genkey[branch] = [variable]
        else:
            profile_boundary_outputs_to_genkey[branch].append(variable)

temp_trend_volume_outputs = pd.read_excel(working_file, volume_variables_tab, engine = "openpyxl", usecols=[0,1,2,3,4,5], skiprows=3).dropna()
trend_volume_outputs = temp_trend_volume_outputs[temp_trend_volume_outputs["Add to Model"].astype(float).eq(1.0)].copy()
trend_volume_outputs_to_genkey = {}

for pipe,sections,variable in zip(trend_volume_outputs["Pipe"], trend_volume_outputs["Section"], trend_volume_outputs["Output"]):
    if isinstance(sections, float):
        sections = int(sections)

    pipesection = [ f"{pipe} {str(sections)}"]

    for pipesec in pipesection:
        if pipesec not in trend_volume_outputs_to_genkey or trend_volume_outputs_to_genkey[pipesec] is None:
            trend_volume_outputs_to_genkey[pipesec] = [variable]
        else:
           trend_volume_outputs_to_genkey[pipesec].append(variable)
        
temp_profile_volume_outputs = pd.read_excel(working_file, volume_variables_tab, engine = "openpyxl", usecols=[7,8,9,10,11], skiprows=3).dropna()
profile_volume_outputs = temp_profile_volume_outputs[temp_profile_volume_outputs["Add to Model.1"].astype(float).eq(1.0)].copy()

profile_volume_outputs_to_genkey = {}

for branch in profile_volume_outputs["Branch Name"].unique():
    for variable in profile_volume_outputs["Output.1"]:
        if branch not in profile_volume_outputs_to_genkey or profile_volume_outputs_to_genkey[branch] is None:
            profile_volume_outputs_to_genkey[branch] = [variable]
        else:
            profile_volume_outputs_to_genkey[branch].append(variable)


### 5- DROP ALL THE DATA COLLECTED INTO THE GENKEY ###

with (
    open(OLGA_genkey, 'r') as original_genkey, 
    open(f"{working_location}\\Updated OLGA Model.opi", "w+") as f
):
    raw_content = original_genkey.read().replace("\\\n", "")  
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw_content.splitlines()]

        ### 5.1 - Materials and walls ###
         
    materials_header_re = re.compile(r"^!\s*library\s+keywords\s*$", re.IGNORECASE)
    try:
        materials_header_idx = next(i for i, line in enumerate(lines) if materials_header_re.match(line))
    except StopIteration:
        raise ValueError("Header not found.")
    

    materials_insert_pos = materials_header_idx + 2
    new_lines = lines[:materials_insert_pos] + materials_to_genkey + lines[materials_insert_pos:]


    ### 5.2 - MF Path and Fluid Name  ###

    MF_header_re = re.compile(r"(FILES\s+PVTFILE\s*=)(.*)", re.IGNORECASE)
    fluid_re = re.compile(r"(?i)(\bFLUID\b\s*=\s*)[^,]*")
    for i, line in enumerate(new_lines):
        if MF_header_re.search(line):
            new_lines[i] = MF_header_re.sub(lambda m: f"{m.group(1)}\"{MF_path_to_genkey}\"",new_lines[i])
        if fluid_re.search(line):
            new_lines[i] = fluid_re.sub(lambda m: f"{m.group(1)}\"{fluid_name}\"", new_lines[i])

   
    ### 5.3 - Geometry ###

    geometry_header_re = re.compile(r'(GEOMETRY\s+LABEL\s*=\s*"GEOM-1")(.*)', re.IGNORECASE)
    try:
        geometry_header_idx = next(i for i, line in enumerate(new_lines) if geometry_header_re.match(line))
    except StopIteration:
        raise ValueError("Header not found.")
    
    geometry_insert_pos = geometry_header_idx + 1
    new_lines[geometry_insert_pos:geometry_insert_pos+1] = geometry_to_genkey

    branch_insert_name = geometry_header_idx - 1
    new_lines[branch_insert_name:branch_insert_name+1] = [f"PARAMETERS LABEL=\"{branch_name}\""]

    ### 5.4 - Boundary Conditions ###
        # OUTLET

    outlet_header_re = re.compile(r'(PARAMETERS\s+LABEL\s*=\s*OUTLET)(.*)', re.IGNORECASE) 
    try:
        outlet_header_idx = next(i for i, line in enumerate(new_lines) if outlet_header_re.match(line))
    except StopIteration:
        raise ValueError("Header not found.")
        
    outlet_new_name = re.compile(r'(?i)(PARAMETERS\s+LABEL\s*=\s*)([^\s,]+)(.*)')
    for key, value in boundary_outlet_changes.items():
        if key.upper() in new_lines[outlet_header_idx]:
            pattern = re.compile(rf"(?i)(\b{re.escape(key)}\b\s*=\s*)[^,]*")
            new_lines[outlet_header_idx] = pattern.sub(lambda m: f"{m.group(1)}{value}", new_lines[outlet_header_idx])
            if boundary_outlet["NODE NAME.2"][0] != "OUTLET":
                new_lines[outlet_header_idx] = outlet_new_name.sub(lambda m: f"{m.group(1)}{boundary_outlet['NODE NAME.2'][0]}{m.group(3)}",new_lines[outlet_header_idx], count=1)
            else:
                continue    
        else:
            continue

        # SOURCE
    source_header_re = re.compile(r'(SOURCE\s+LABEL\s*=\s*)(.*)', re.IGNORECASE) 

    try:
        source_header_idx = next(i for i, line in enumerate(new_lines) if source_header_re.match(line))
    except StopIteration:
        raise ValueError("Header not found.")
    
    source_location = re.compile(r'(\bPIPE\s*=\s*"?)([^",\s]+)("?)', re.IGNORECASE)
    new_lines[source_header_idx] = source_location.sub(lambda m: f"{m.group(1)}{first_pipe_name}{m.group(3)}", new_lines[source_header_idx], count = 1)


    source_new_name = re.compile(r'(?i)(SOURCE\s+LABEL\s*=\s*)([^\s,]+)(.*)')
    new_lines[source_header_idx] = source_new_name.sub(lambda m: f"{m.group(1)}{boundary_source['NODE NAME.1'][0]}{m.group(3)}",new_lines[source_header_idx], count=1)
   
   
    pieces = []

    for key, value in boundary_source_changes.items():
        pieces.append(f"{key}={value}")

        if key == "STDFLOWRATE":
           pieces.append(f"PHASE={boundary_source["PHASE"][0]}")

    source_parameters = ", ".join(pieces)
    new_lines[source_header_idx] = f'{new_lines[source_header_idx]}, {source_parameters}'
           

        #INLET
    inlet_header_re = re.compile(r'(PARAMETERS\s+LABEL\s*=\s*INLET)(.*)', re.IGNORECASE) 
    try:
        inlet_header_idx = next(i for i, line in enumerate(new_lines) if inlet_header_re.match(line))
    except StopIteration:
        raise ValueError("Header not found.")

    inlet_new_name = re.compile(r'(?i)(PARAMETERS\s+LABEL\s*=\s*)([^\s,]+)(.*)')
    if boundary_inlet["NODE NAME"][0] != "INLET":
        new_lines[inlet_header_idx] = inlet_new_name.sub(lambda m: f"{m.group(1)} \"{boundary_inlet['NODE NAME'][0]}\" {m.group(3)}",new_lines[inlet_header_idx], count=1)

                  
    ### Variables ###
        # Trend

    trenddata_header_re = re.compile(r'^.*TRENDDATA PIPE=.*$')
    try:
        trenddata_header_idx = next(i for i, line in enumerate(new_lines) if trenddata_header_re.match(line))
    except StopIteration:
        raise ValueError("Header not found.")
    trend_line = new_lines[trenddata_header_idx]
    pattern = re.compile(r'(\b[A-Za-z_][A-Za-z0-9_]*)\s*=\s*("([^"\\]|\\.)*"|\([^()]*\)|[^,\s)]+)')
    generated_lines = []


    for key, value in trend_boundary_outputs_to_genkey.items():
        pipename = key.split(" ")[0]
        sectioninpipe = key.split(" ")[1]
        vars_str = ",".join(value) if isinstance(value,(list,tuple)) else str(value)
        new_line = trend_line
        
        new_line = pattern.sub( lambda m: (f"{m.group(1)}=" + ((f'"{pipename}"' if m.group(2).startswith('"') else str(pipename)) if m.group(1) == 'PIPE'                        
                        else f'({str(sectioninpipe)})' if m.group(1) == 'SECTION'
                        else (f'({vars_str})' if m.group(1) == 'VARIABLE' and m.group(2).startswith('(') else vars_str)
                        if m.group(1) in ('PIPE', 'SECTION', 'VARIABLE') else m.group(2))),new_line )

        generated_lines.append(new_line)

    for key, value in trend_volume_outputs_to_genkey.items():
        pipename = key.split(" ")[0]
        sectioninpipe = key.split(" ")[1]
        vars_str = ",".join(value) if isinstance(value,(list,tuple)) else str(value)
        new_line = trend_line
        
        new_line = pattern.sub( lambda m: (f"{m.group(1)}=" + ((f'"{pipename}"' if m.group(2).startswith('"') else str(pipename)) if m.group(1) == 'PIPE'                        
                        else f'({str(sectioninpipe)})' if m.group(1) == 'SECTION'
                        else (f'({vars_str})' if m.group(1) == 'VARIABLE' and m.group(2).startswith('(') else vars_str)
                        if m.group(1) in ('PIPE', 'SECTION', 'VARIABLE') else m.group(2))),new_line )

        generated_lines.append(new_line)

   

    # Profile

    profiledata_header_re = re.compile(r'^.*PROFILEDATA VARIABLE=.*$')
    try:
        profile_data_header_idx = next(i for i, line in enumerate(new_lines) if profiledata_header_re.match(line))
    except StopIteration:
        raise ValueError("Header not found.")
    profile_line = new_lines[profile_data_header_idx]
    pattern = re.compile(r'(\b[A-Za-z_][A-Za-z0-9_]*)\s*=\s*("([^"\\]|\\.)*"|\([^()]*\)|[^,\s)]+)')
    
    for key, value in profile_boundary_outputs_to_genkey.items():
        
        vars_str = ",".join(value) if isinstance(value,(list,tuple)) else str(value)
        new_line = profile_line
        
        new_line = pattern.sub( lambda m: (f"{m.group(1)}=" f'({vars_str})' if m.group(1) == 'VARIABLE'
                         else f"{m.group(1)}={m.group(2)}"),new_line)

        generated_lines.append(new_line)

    for key, value in profile_volume_outputs_to_genkey.items():
        
        vars_str = ",".join(value) if isinstance(value,(list,tuple)) else str(value)
        new_line = profile_line
        
        new_line = pattern.sub( lambda m: (f"{m.group(1)}=" f'({vars_str})' if m.group(1) == 'VARIABLE'
                         else f"{m.group(1)}={m.group(2)}"),new_line)

        generated_lines.append(new_line)

    new_lines[trenddata_header_idx:trenddata_header_idx+2] = generated_lines  

        

    a = 5    
       
            







        


            

    f.write("\n".join(new_lines))
f.close()
original_genkey.close()
         

a=5