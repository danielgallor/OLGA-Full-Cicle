# Imports
from iep import IEP
import pandas as pd
from Load_Genkey_rev2 import load_Genkey
import copy
import pyfas as fa
from TransformKey import transform_2015_to_2018
import zipfile
from pathlib import Path
import scipy.interpolate
import re
import os
import subprocess # nosec
import numpy as np
import time


def olga_version_check(OLGA_exe, base_genkey):
    #OLGA VERSION CHECK#
    if OLGA_exe.split("\\")[-1].split(".")[0] == "OLGA-2018":
        base_genkey = transform_2015_to_2018(base_genkey)
        return (2018, base_genkey)
    return (2015, base_genkey)


def dump_files(fluid_files):
    # write tab file(s) to working location (so that OLGA can find them when it runs later)
    try:
        with zipfile.ZipFile(fluid_files) as zip_ref:
            zip_ref.extractall(working_location)
    except:
        flux.log("No Fluid Files Found")

    with open(network_model_wells, 'r') as ff, open(f"{working_location}//{Path(network_model_wells).stem} base genkey.genkey", 'w+') as gg:
        lines = ff.readlines()
        gg.writelines(lines)
    with open(network_model_mass_source, 'r') as ff, open(f"{working_location}//{Path(network_model_mass_source).stem} base genkey.genkey", 'w+') as gg:
        lines = ff.readlines()
        gg.writelines(lines)
    with open(wells_genkey, 'r') as ff, open(f"{working_location}//{Path(wells_genkey).stem} base genkey.genkey", 'w+') as gg:
        lines = ff.readlines()
        gg.writelines(lines)


def check_production_profile():
    for well in well_data:
        well_profiles[well["Label"]] = copy.deepcopy(df_production_profile[well['Label']])
        well_profiles[well["Label"]].columns = well_profiles[well["Label"]].iloc[0]
        well_profiles[well["Label"]] = well_profiles[well["Label"]].iloc[:len([x for x in well_profiles[well["Label"]]["Cumulative Gas Production"] if x])][1:]
        
        if branch_cumulative_gas_production_record and branch_cumulative_gas_production_record[-1][well["Branch"]]: # If wells have been producing, look up current variables from production profile
            current_cummulative_prod = branch_cumulative_gas_production_record[-1][well["Branch"]] # how much the well has produced after time step
            header_rows = well_profiles[well["Label"]].iloc[:1]
            data_rows = well_profiles[well["Label"]].iloc[1:]
            current_data = data_rows[data_rows["Cumulative Gas Production"].astype(float) < current_cummulative_prod] # new data up to cumumulative production
            well_profiles[well["Label"]] = pd.concat([header_rows, current_data])
            reservoir_pressures[well['Label']] = round(float([value for value in well_profiles[well["Label"]]["RESPRESSURE"].values if value][-1]), 2)
            reservoir_cgrs[well['Label']] = round(float([value for value in well_profiles[well["Label"]]["CGR"].values if value][-1]), 2)
            reservoir_wgrs[well['Label']] = round(float([value for value in well_profiles[well["Label"]]["WGR"].values if value][-1]), 2)
        else:
            well_profiles[well["Label"]] = well_profiles[well["Label"]].iloc[:2]
            reservoir_pressures[well['Label']] = round(float(well_profiles[well["Label"]]["RESPRESSURE"][3]), 2)
            reservoir_cgrs[well['Label']] = round(float(well_profiles[well["Label"]]["CGR"][3]), 2)
            reservoir_wgrs[well['Label']] = round(float(well_profiles[well["Label"]]["WGR"][3]), 2)

    
def update_change_dict_network_mass(well_rates):
    change_dict = {}
    pressure = " ".join(get_current_suction_pressure())
    for well in well_data:
        well_rate = well_rates[well['Mass Source']]
        try:
            well_temp = well_choke_ds_temps[well['Label']]
        except:
            well_temp = well_FWHTs[well['Label']] # Inital estimate before choke D/S T calc
        try:
            # update rate
            change_dict["SOURCE"][0].append("LABEL")
            change_dict["SOURCE"][1].append(well['Mass Source'])
            change_dict["SOURCE"][2].append("STDFLOWRATE")
            change_dict["SOURCE"][3].append(f"{well_rate} MMscf/d")
            # update temp
            change_dict["SOURCE"][0].append("LABEL")
            change_dict["SOURCE"][1].append(well['Mass Source'])
            change_dict["SOURCE"][2].append("TEMPERATURE")
            change_dict["SOURCE"][3].append(f"{well_temp} C")
            if well['Label'] in offline_wells or well['Label'] in future_wells:
                # turn off MEG
                change_dict["SOURCE"][0].append("LABEL")
                change_dict["SOURCE"][1].append(well["MEG Source"])
                change_dict["SOURCE"][2].append("STDFLOWRATE")
                change_dict["SOURCE"][3].append("0 Sm3/h") # Changes the offline well MEG rate to 0
        except:
            change_dict["SOURCE"] = [
                ["LABEL", "LABEL"],
                [well['Mass Source'], well['Mass Source']],
                ["STDFLOWRATE", "TEMPERATURE"],
                [f"{well_rate} MMscf/d", f"{well_temp} C"]
            ]
            if well['Label'] in offline_wells or well['Label'] in future_wells:
                change_dict["SOURCE"][0].append("LABEL")
                change_dict["SOURCE"][1].append(well["MEG Source"])
                change_dict["SOURCE"][2].append("STDFLOWRATE")
                change_dict["SOURCE"][3].append("0 Sm3/h") # Changes the offline well MEG rate to 0
    change_dict["PARAMETERS"] = [
        ["LABEL"],
        [arrival_facility_label],
        ["PRESSURE"],
        [pressure]
    ] # append latest arrvial pressure (if compression is online this will change)
    return change_dict       


def update_change_dict_wells(well_rates):
    change_dict = {}
    for well in well_data:
        well_prod_index = get_prod_index(well)
        if branch_cumulative_gas_production_record: # If wells have been producing, look up current variables from production profile
            reservoir_pressure = [value for value in well_profiles[well["Label"]]["RESPRESSURE"].values if value][-1] + " " + well_profiles[well["Label"]]["RESPRESSURE"][2]
            well_fbhp = ("PRESSURE", calculate_flowing_bottom_hole_pressure(reservoir_pressure, well_prod_index, well_rates[well['Mass Source']]))
            cgr = ("CGR", [value for value in well_profiles[well["Label"]]["CGR"].values if value][-1] + " " + well_profiles[well["Label"]]["CGR"][2])
            wgr = ("WGR", [value for value in well_profiles[well["Label"]]["WGR"].values if value][-1] + " " + well_profiles[well["Label"]]["WGR"][2])
        else:
            reservoir_pressure = well_profiles[well["Label"]]["RESPRESSURE"][3] + " " + well_profiles[well["Label"]]["RESPRESSURE"][2]
            well_fbhp = ("PRESSURE", calculate_flowing_bottom_hole_pressure(reservoir_pressure, well_prod_index, well_rates[well['Mass Source']]))
            cgr = ("CGR", well_profiles[well["Label"]]["CGR"][3] + " " + well_profiles[well["Label"]]["CGR"][2])
            wgr = ("WGR", well_profiles[well["Label"]]["WGR"][3] + " " + well_profiles[well["Label"]]["WGR"][2])
        well_rate = ("STDFLOWRATE", f"-{well_rates[well['Mass Source']]} MMscf/d") if (well['Label'] not in offline_wells and well['Label'] not in future_wells) else ("STDFLOWRATE", f"0.01 MMscf/d") # the abandoned wells need some small rate to not crash the model
        # well_rate = ("STDFLOWRATE", f"-{well_rates[well['Mass Source']]} MMscf/d")
        for variable in [well_fbhp, cgr, wgr, well_rate]:
            try:
                change_dict["PARAMETERS"][0].append("LABEL")
                change_dict["PARAMETERS"][1].append(well['Label'] if variable[0] != "STDFLOWRATE" else well['Mass Source'])
                change_dict["PARAMETERS"][2].append(variable[0])
                change_dict["PARAMETERS"][3].append(variable[1])
            except:
                change_dict["PARAMETERS"] = [
                    ["LABEL"],
                    [well['Label'] if variable[0] != "STDFLOWRATE" else well['Mass Source']],
                    [variable[0]],
                    [variable[1]]
                ]
    return change_dict


def update_change_dict_network(compression="bypass", first_run_of_timestep=False, force_run_at_max_compressor_suction=False):
    change_dict = {}
    for well in well_data:
        if OLGA_V == 2015:
            for variable in ["RESPRESSURE", "WGR", "CGR"]:
                try:
                    change_dict["WELL"][0].append("LABEL")
                    change_dict["WELL"][1].append(well['Label'])
                    change_dict["WELL"][2].append(variable)
                    change_dict["WELL"][3].append(
                        well_profiles[well["Label"]][variable][3] + " " + well_profiles[well["Label"]][variable][2] if not branch_cumulative_gas_production_record else \
                            [value for value in well_profiles[well["Label"]][variable].values if value][-1] + " " + well_profiles[well["Label"]][variable][2]
                        )
                except:
                    change_dict["WELL"] = [
                        ["LABEL"],
                        [well['Label']],
                        [variable],
                        ([well_profiles[well["Label"]][variable][3] + " " + well_profiles[well["Label"]][variable][2]]) if not branch_cumulative_gas_production_record else \
                            ([[value for value in well_profiles[well["Label"]][variable].values if value][-1] + " " + well_profiles[well["Label"]][variable][2]])
                    ]                  
        elif OLGA_V == 2018:
            for variable in ["PRESSURE", "WGR", "CGR"]:
                try:
                    change_dict["RESERVOIRCONTACT"][0].append("LABEL")
                    change_dict["RESERVOIRCONTACT"][1].append(well['Label'])
                    change_dict["RESERVOIRCONTACT"][2].append(variable)
                    change_dict["RESERVOIRCONTACT"][3].append(
                        well_profiles[well["Label"]][variable][3] + " " + well_profiles[well["Label"]][variable][2] if not branch_cumulative_gas_production_record else \
                            [value for value in well_profiles[well["Label"]][variable].values if value][-1] + " " + well_profiles[well["Label"]][variable][2]
                        )        
                except:
                    change_dict["RESERVOIRCONTACT"] = [
                        ["LABEL"],
                        [well['Label']],
                        [variable],
                        ([well_profiles[well["Label"]][variable][3] + " " + well_profiles[well["Label"]][variable][2]]) if not branch_cumulative_gas_production_record else \
                            ([[value for value in well_profiles[well["Label"]][variable].values if value][-1] + " " + well_profiles[well["Label"]][variable][2]])
                    ]
        if well["Label"] in future_wells: # If the well is not yet online (to be added later in life) keep wing valve closed and shut off MEG
            try:
                change_dict["VALVE"][0].append("LABEL")
                change_dict["VALVE"][1].append(well["Wing Valve"])
                change_dict["VALVE"][2].append("OPENING")
                change_dict["VALVE"][3].append("0")
            except:
                change_dict["VALVE"] = [
                    ["LABEL"],
                    [well["Wing Valve"]],
                    ["OPENING"],
                    ["0"]
                ]
            try:
                change_dict["SOURCE"][0].append("LABEL")
                change_dict["SOURCE"][1].append(well["MEG Source"])
                change_dict["SOURCE"][2].append("STDFLOWRATE")
                change_dict["SOURCE"][3].append("0 Sm3/h")
            except:
                change_dict["SOURCE"] = [
                    ["LABEL"],
                    [well["MEG Source"]],
                    ["STDFLOWRATE"],
                    ["0 Sm3/h"]
                ]
        else:  # If the well is online keep wing valve open, even if the well is abandoned -> as this only affects maximum potential model, rate will be zero-ed in other models
            try:
                change_dict["VALVE"][0].append("LABEL")
                change_dict["VALVE"][1].append(well["Wing Valve"])
                change_dict["VALVE"][2].append("OPENING")
                change_dict["VALVE"][3].append("1")
            except:
                change_dict["VALVE"] = [
                    ["LABEL"],
                    [well["Wing Valve"]],
                    ["OPENING"],
                    ["1"]
                ]
            # MEG will come back online as per the default genkey flow rate
    if first_run_of_timestep:
        if current_day != 0: # get the most recent suction pressure to make sure this is carried through
            pressure = " ".join(get_last_suction_pressure())
            change_dict["PARAMETERS"] = [
                ["LABEL"],
                [arrival_facility_label],
                ["PRESSURE"],
                [pressure]
            ]
        else:
            change_dict["PARAMETERS"] = [
                ["LABEL"],
                [arrival_facility_label],
                ["PRESSURE"],
                [str(plant_backpressure) + ' barg']
            ]
    elif force_run_at_max_compressor_suction:
        change_dict["PARAMETERS"] = [
                ["LABEL"],
                [arrival_facility_label],
                ["PRESSURE"],
                [str(maximum_compressor_suction_pressure) + " barg"]
            ]
    else:
        if compression == "increase" or compression == "decrease":
            pressure = get_current_suction_pressure()
            change_dict["PARAMETERS"] = [
                ["LABEL"],
                [arrival_facility_label],
                ["PRESSURE"],
                [(str(max(minimum_compressor_suction_pressure, float(pressure[0]) - 2)) + " " + pressure[1]) if compression == "increase" else \
                    (str(min(maximum_compressor_suction_pressure, float(pressure[0]) + 2)) + " " + pressure[1])]
            ]
        elif compression == "bypass":
            change_dict["PARAMETERS"] = [
                    ["LABEL"],
                    [arrival_facility_label],
                    ["PRESSURE"],
                    [str(plant_backpressure) + " barg"]
            ]
    return change_dict


def get_last_suction_pressure():
    with open(f"{working_location}\\{iteration_name.split('day ')[0]}day {int(iteration_name.split('day ')[1]) - time_step_days} max potential.genkey", "r") as f:
        lines = [re.sub(r"\s\s", "", x) for x in "".join([x.replace("\\\n", "") for x in f.readlines()]).split("\n")]
        for line in lines:
            if f'PARAMETERS LABEL={arrival_facility_label}' in line:
                previous_suction_pressure = re.search(rf'PRESSURE=[a-zA-Z0-9()"/.,\s\-]+(?![a-zA-Z]*=)', line).group().split("=")[1].split(" ")
                previous_suction_pressure[1] = previous_suction_pressure[1].replace(",", "")
    return previous_suction_pressure # returns pressure + units


def get_current_suction_pressure():
    with open(f"{working_location}\\{iteration_name} max potential.genkey", "r") as f:
        lines = [re.sub(r"\s\s", "", x) for x in "".join([x.replace("\\\n", "") for x in f.readlines()]).split("\n")]
        for line in lines:
            if f'PARAMETERS LABEL={arrival_facility_label}' in line:
                current_suction_pressure = re.search(rf'PRESSURE=[a-zA-Z0-9()"/.,\s\-]+(?![a-zA-Z]*=)', line).group().split("=")[1].split(" ")
                current_suction_pressure[1] = current_suction_pressure[1].replace(",", "")
    return current_suction_pressure # returns pressure + units


def get_prod_index(well):
    well_label = well['Label']
    with open(network_model_wells, "r") as f:
        lines = [re.sub(r"\s\s", "", x) for x in "".join([x.replace("\\\n", "") for x in f.readlines()]).split("\n")]
        for line in lines:
            if f'WELL LABEL="{well_label}"' in line:
                well_prod_index = re.search(rf'PRODI=[a-zA-Z0-9()"/.,\s\-]+(?![a-zA-Z]*=)', line).group().split("=")[1].split(" ")[0]
    return well_prod_index
    

def run_simulation(genkey, working_location, iteration_name, OLGA_executable):
    filename = f"{working_location}\\{iteration_name}.bat"
    genkey_call = f"call \"{OLGA_executable}\" \"%s" % genkey.replace('.genkey', '.genkey"')

    with open(filename, 'w+') as f:
        f.flush()
        f.write('@echo off\npushd "' + working_location + '"' + "\n")
        f.write("%s\n" % genkey_call)
        f.write("popd\nexit")

    subprocess.call(filename) # nosec


def genkey_setup_and_run(change_dict, iteration_name, base_genkey):
    output_genkey = flux.add_output_file("Output Genkeys", f"{working_location}\\{iteration_name}.genkey")
    load_Genkey(base_genkey, output_genkey, change_dict)
    run_simulation(output_genkey, working_location, iteration_name, OLGA_executable)


def OLGA_variable_extractor(flowline, location, olga_variable, iteration_name, timestep="last"):
    try:
        ppl = fa.Ppl(f"{working_location}\\{iteration_name}.ppl") # sometimes OLGA is too slow to release the .ppl before pyfas tries to pick it up
    except:
        flux.log(f"OLGA jumped the gun on {iteration_name}.ppl")
        flux.log(f"sleeping 1 s....")
        time.sleep(1)
        ppl = fa.Ppl(f"{working_location}\\{iteration_name}.ppl") # sometimes OLGA is too slow to release the .ppl before pyfas tries to pick it up

    if location == "branch": # branch variables use .tpl not .ppl
        try:
            tpl = fa.Tpl(f"{working_location}\\{iteration_name}.tpl") # sometimes OLGA is too slow to release the .tpl before pyfas tries to pick it up
        except:
            flux.log(f"OLGA jumped the gun on {iteration_name}.tpl")
            flux.log(f"sleeping 1 s....")
            time.sleep(1)
            tpl = fa.Tpl(f"{working_location}\\{iteration_name}.tpl") # sometimes OLGA is too slow to release the .tpl before pyfas tries to pick it up

    if location == "branch":
        try:
            data_points = tpl.filter_trends(olga_variable)
        except:
            flux.log(f"OLGA jumped the gun on {iteration_name}.tpl")
            flux.log(f"sleeping 1 s....")
            time.sleep(1)
            data_points = tpl.filter_trends(olga_variable)
        for key in list(data_points.keys()):
            if (flowline.upper() in data_points[key].upper() and olga_variable in data_points[key][:len(olga_variable)]):
                try: # sometimes the OLGA run fails, try it again
                    tpl.extract(key)
                except:
                    flux.log(f"OLGA failed on {iteration_name}.tpl")
                    subprocess.call(f"{working_location}\\{iteration_name}.bat") # nosec
                    time.sleep(1)
                    tpl.extract(key)
                # branch variables cannot be taken at the start or end of the flowline - it is the whole branch
                if timestep == "last":
                    return tpl.data[key][-1] # take last time step
                elif timestep == "first":
                    return tpl.data[key][0] # take first time step
    else:
        try:
            data_points = ppl.filter_data(olga_variable)
        except:
            flux.log(f"OLGA jumped the gun on {iteration_name}.ppl")
            flux.log(f"sleeping 1 s....")
            time.sleep(1)
            data_points = ppl.filter_data(olga_variable)
        for key in list(data_points.keys()):
            if (flowline.upper() in data_points[key].upper() and olga_variable in data_points[key][:len(olga_variable)]):
                try: # sometimes the OLGA run fails, try it again
                    ppl.extract(key)
                except:
                    flux.log(f"OLGA failed on {iteration_name}.ppl")
                    subprocess.call(f"{working_location}\\{iteration_name}.bat") # nosec
                    time.sleep(1)
                    ppl.extract(key)
                if location == "start":
                    if timestep == "last":
                        return ppl.data[key][-1][-1][0] # take last time step at START of flowline
                    elif timestep == "first":
                        return ppl.data[key][-1][0][0] # take first time step at START of flowline
                elif location == "end":
                    if timestep == "last":
                        return ppl.data[key][-1][-1][-1] # take last time step at END of flowline
                    elif timestep == "first":
                        return ppl.data[key][-1][0][-1] # take first time step at END of flowline


def extract_branch_data(iteration_name, timestep):
    for well in well_data:
        branch_gas_rates[well["Branch"]] = round(OLGA_variable_extractor(well["Branch"], "end", "QGST", iteration_name, timestep) * Sm3_s_to_MMscf_d, 2)
        branch_cumulative_gas_production[well["Branch"]] = round(branch_gas_rates[well["Branch"]] * time_step_days, 2)
        branch_oil_rates[well['Branch']] = round(branch_gas_rates[well["Branch"]] * reservoir_cgrs[well['Label']])
        branch_water_rates[well['Branch']] = round(branch_gas_rates[well["Branch"]] * reservoir_wgrs[well['Label']])
    # if 'max potential' in iteration_name: # if the max potential simulation is being used - set the rates for offline / future wells to 0 as they would be in the mass source sims
    #     # MAY HAVE TO DETELTE THIS AND RUN THE MASS SOURCE MODEL ANYWAY SO THAT THE CORRECT NUMBERS ARE USED IN POST PROCESSING!!!! ! # MS 18/02/22
    #     for well in [well_ for well_ in well_data if well_["Label"] in future_wells or well_["Label"] in offline_wells]:
    #         branch_gas_rates[well["Branch"]] = 0
    #         branch_cumulative_gas_production[well["Branch"]] = 0
    #         branch_oil_rates[well['Branch']] = 0
    #         branch_water_rates[well['Branch']] = 0
    # LIQC extraction - all branches
    for branch in liqc_branches:
        branch_liqc[branch] = round(OLGA_variable_extractor(branch, "branch", "LIQC", iteration_name, timestep) * Sm3_s_to_MMscf_d, 2)
    record_branch_data()


def append_export_line_data(iteration_name, timestep): # Not used currently
    ## Point to the Export Pipeline - where outputs will be examined ##
    export_pipeline_gas_rate.append(round(OLGA_variable_extractor(export_pipeline, "end", "QGST", iteration_name, timestep) * Sm3_s_to_MMscf_d, 2))
    export_pipeline_oil_rate.append(round(OLGA_variable_extractor(export_pipeline, "end", "QOST", iteration_name, timestep) * Sm3_s_to_STB_d, 2))
    export_pipeline_water_rate.append(round(OLGA_variable_extractor(export_pipeline, "end", "QWST", iteration_name, timestep) * Sm3_s_to_STB_d, 2))
    export_pipeline_WGR.append(round(OLGA_variable_extractor(export_pipeline, "end",  "WGR", iteration_name, timestep) * Sm3_Sm3_to_STB_MMscf, 2))
    export_pipeline_CGR.append(round(OLGA_variable_extractor(export_pipeline, "end", "CGR", iteration_name, timestep) * Sm3_Sm3_to_STB_MMscf, 2))


def record_branch_data():
    branch_gas_rates_record.append(copy.deepcopy(branch_gas_rates))
    branch_oil_rates_record.append(copy.deepcopy(branch_oil_rates))
    branch_water_rates_record.append(copy.deepcopy(branch_water_rates))
    branch_liqc_record.append(copy.deepcopy(branch_liqc))


def process_outputs(current_day, iteration_name, timestep="last"):
    extract_branch_data(iteration_name, timestep)
    # append_export_line_data(iteration_name, timestep)
    reservoir_pressures_record.append(copy.deepcopy(reservoir_pressures))
    name_record.append(iteration_name)
    time_record.append(current_day)
    record_cumulative_gas_production(current_day)
    well_FWHPs_record.append(well_FWHPs)
    well_FWHTs_record.append(well_FWHTs)
    well_backpressures_record.append(well_backpressures)
    well_choke_ds_temps_record.append(well_choke_ds_temps)


def extract_top_hole_conditions(iteration_name):
    for well in well_data:
        well_FWHTs[well["Label"]] = round(OLGA_variable_extractor(well["Well Flowline"], "end", "TM", iteration_name), 2)
        well_FWHPs[well["Label"]] = round(OLGA_variable_extractor(well["Well Flowline"], "end", "PT", iteration_name), 2)


def extract_backpressures(iteration_name, timestep):
    for well in well_data:
        well_backpressures[well["Label"]] = round(OLGA_variable_extractor(well["Branch"], "start", "PT", iteration_name, timestep), 2)


def record_cumulative_gas_production(current_day):
    if current_day == 0:
        branch_cumulative_gas_production_record.append(branch_cumulative_gas_production)
        branch_max_potential_cumulative_gas_production_record.append(branch_maximum_potential_cumulative_gas_production)
    else:
        current_cumulative = copy.deepcopy(branch_cumulative_gas_production_record[-1])
        current_max_potential_cumulative = copy.deepcopy(branch_cumulative_gas_production_record[-1])
        for branch in current_cumulative:
            current_cumulative[branch] += branch_cumulative_gas_production[branch]
            current_max_potential_cumulative[branch] += branch_maximum_potential_cumulative_gas_production[branch]
        branch_cumulative_gas_production_record.append(current_cumulative)
        branch_max_potential_cumulative_gas_production_record.append(current_max_potential_cumulative)


def abandon_check(offline_wells):
    if current_day != 0:
        if list(branch_maximum_potential_gas_rates.values()) == list(branch_maximum_potential_gas_rates_record[-2].values()) == list(branch_maximum_potential_gas_rates_record[-3].values()): # If the end of the production profiles has been reached but is still higher than the abandonment conditions
                return [well["Label"] for well in well_data] # Abandon all wells - LOF will continue endlessly due to production profile data.
    for well in well_data: 
        if branch_maximum_potential_gas_rates[well["Branch"]] < abandon_prod_rate and well["Label"] not in future_wells:
            if well["Label"] not in offline_wells: 
                offline_wells.append(well["Label"])
                flux.log(f"Closing {well['Label']}... Reservoir Pressure: {reservoir_pressures[well['Label']]} psig, Max. Potential Production Rate: {branch_maximum_potential_gas_rates[well['Branch']]} MMscf/d\n")
        else: # If the well can now produce above the abandon rate, bring it back online (e.g. if compression comes online)
            offline_wells = [well_ for well_ in offline_wells if well_ != well["Label"]]
    return offline_wells


def compression_check():
    if sum([value for branch, value in branch_maximum_potential_gas_rates.items() if ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in overridden_wells) and ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in future_wells)]) + \
        sum([min(branch_maximum_potential_gas_rates[[well_["Branch"] for well_ in well_data if well_["Label"] == well][0]], overridden_wells[well]) for well in overridden_wells]) < rate_limit: # wells cannot meet production
        while (sum([value for branch, value in branch_maximum_potential_gas_rates.items() if ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in overridden_wells) and ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in future_wells)]) + \
        sum([min(branch_maximum_potential_gas_rates[[well_["Branch"] for well_ in well_data if well_["Label"] == well][0]], overridden_wells[well]) for well in overridden_wells]) < rate_limit) and (float(get_current_suction_pressure()[0]) > float(minimum_compressor_suction_pressure)):
            if float(get_current_suction_pressure()[0]) == plant_backpressure:
                run_maximum_potential(force_run_at_max_compressor_suction=True) # forces max potential case to be run with maximum compressor suction pressure (cannot operate between plant backpressure and comp. max. suction pressure)
            else:
                run_maximum_potential(compression="increase") # checks if total potential rate of field is less than rate limit, if so, drops arrival pressure incrementally until potential rate meets limit or minimum suction pressure is reached.

    elif sum([value for branch, value in branch_maximum_potential_gas_rates.items() if ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in overridden_wells) and ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in future_wells)]) + \
        sum([min(branch_maximum_potential_gas_rates[[well_["Branch"] for well_ in well_data if well_["Label"] == well][0]], overridden_wells[well]) for well in overridden_wells]) > rate_limit*1.05: # wells can do more than 5% above production limit
        while (sum([value for branch, value in branch_maximum_potential_gas_rates.items() if ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in overridden_wells) and ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in future_wells)]) + \
        sum([min(branch_maximum_potential_gas_rates[[well_["Branch"] for well_ in well_data if well_["Label"] == well][0]], overridden_wells[well]) for well in overridden_wells]) > rate_limit*1.05) and (float(get_current_suction_pressure()[0]) < float(maximum_compressor_suction_pressure)):
            if float(get_current_suction_pressure()[0]) >= maximum_compressor_suction_pressure:
                run_maximum_potential(compression="bypass") # try bypass
                if sum([value for branch, value in branch_maximum_potential_gas_rates.items() if ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in overridden_wells) and ([well for well in well_data if well['Branch'] == branch][0]['Label'] not in future_wells)]) + \
                    sum([min(branch_maximum_potential_gas_rates[[well_["Branch"] for well_ in well_data if well_["Label"] == well][0]], overridden_wells[well]) for well in overridden_wells]) < rate_limit:
                    run_maximum_potential(force_run_at_max_compressor_suction=True) # forces max potential case to be run with maximum compressor suction pressure as this is best case scenario
            else:
                run_maximum_potential(compression="decrease") # checks if total potential rate of field is more than rate limit, if so, increase arrival pressure incrementally until potential rate meets limit or maximum suction pressure is reached.


def run_maximum_potential(compression="bypass", first_run_of_timestep=False, force_run_at_max_compressor_suction=False):
    if not os.path.exists(f"{working_location}\\{iteration_name} max potential.ppl") or not first_run_of_timestep:
        network_change_dict = update_change_dict_network(compression, first_run_of_timestep, force_run_at_max_compressor_suction)
        genkey_setup_and_run(network_change_dict, iteration_name + " max potential", network_model_wells)
    for well in well_data:
        branch_maximum_potential_gas_rates[well["Branch"]] = round(OLGA_variable_extractor(well["Branch"], "end", "QGST", iteration_name + " max potential") * Sm3_s_to_MMscf_d, 2)
        branch_maximum_potential_cumulative_gas_production[well["Branch"]] = round(branch_maximum_potential_gas_rates[well["Branch"]] * time_step_days, 2)
        branch_maximum_potential_condensate_rates[well["Branch"]] = round(branch_maximum_potential_gas_rates[well["Branch"]] * reservoir_cgrs[well['Label']], 2)
        branch_maximum_potential_water_rates[well["Branch"]] = round(branch_maximum_potential_gas_rates[well["Branch"]] * reservoir_wgrs[well['Label']], 2)


def record_max_potentials():
    branch_maximum_potential_gas_rates_record.append(copy.deepcopy(branch_maximum_potential_gas_rates))
    branch_maximum_potential_condensate_rates_record.append(copy.deepcopy(branch_maximum_potential_condensate_rates))
    branch_maximum_potential_water_rates_record.append(copy.deepcopy(branch_maximum_potential_water_rates))


def ratio_production(rate_limit, overridden_wells, rates, offline_wells, future_wells):
    total_potential_flow = sum([value for branch, value in branch_maximum_potential_gas_rates.items() if ([well["Label"] for well in well_data if well['Branch'] == branch][0] not in offline_wells) and ([well["Label"] for well in well_data if well['Branch'] == branch][0] not in future_wells)]) # Total potential flow from all wells (when all wells flowing...)
    
    if overridden_wells: # If some wells have been manually overriden, this needs to be accounted for in the total potential (taken out)
        for well_label in overridden_wells:
            well = [well_ for well_ in well_data if well_['Label'] == well_label][0]
            total_potential_flow = total_potential_flow - branch_maximum_potential_gas_rates[well['Branch']]
            if overridden_wells[well_label] < branch_maximum_potential_gas_rates[well['Branch']]:
                rate_limit = rate_limit - overridden_wells[well_label]
                rates[well["Mass Source"]] = overridden_wells[well_label]
            else: 
                rate_limit = rate_limit - branch_maximum_potential_gas_rates[well['Branch']]
                rates[well["Mass Source"]] = str(round(branch_maximum_potential_gas_rates[well['Branch']], 2))
    
    try:
        ratio = round(rate_limit / total_potential_flow, 3) # ratio
    except:
        ratio = 0
    
    for well in well_data:
        if well["Label"] in offline_wells or well["Label"] in future_wells:
            rates[well["Mass Source"]] = "0.00001"
        else:
            if well['Label'] not in overridden_wells:
                if ratio >= 1:
                    rates[well["Mass Source"]] = str(round(branch_maximum_potential_gas_rates[well["Branch"]], 2)) # set to max potential rate
                if 0 < ratio < 1:
                    rates[well["Mass Source"]] = str(round(branch_maximum_potential_gas_rates[well["Branch"]] * ratio, 2)) # apply ratio to max potential rate

    return rates


def optimise_condensate(rate_limit, overridden_wells, offline_wells, rates, logic):
    '''
    FUNCTION NOT IN USE : LOGIC DOES NOT YET WORK
    '''
    # Get CGRs
    sorted_well_CGRs = [[well for well in well_data if well["Label"] == item[0]][0] for item in sorted(reservoir_cgrs.items(), key=lambda item: item[1], reverse=(True if logic == 'max' else False)) if item[0] not in overridden_wells]

    remaining_rate = rate_limit
    for well in sorted_well_CGRs:
        if remaining_rate == 0.00001:
            if well['Label'] not in offline_wells: offline_wells.append(well['Label']) # Well is on standby if theres still wells to produce but no capacity available
            rates[well['Mass Source']] = '0.00001'
        elif branch_maximum_potential_gas_rates[well["Branch"]] < remaining_rate:
            rates[well['Mass Source']] = str(round(branch_maximum_potential_gas_rates[well["Branch"]], 2)) # Maximise the prioritised well (set to max potential)  WARNING: This max potential is only true if other wells are flowing at max potential... (so it can likely do more..)
            remaining_rate = round(remaining_rate - branch_maximum_potential_gas_rates[well["Branch"]], 2) 
            offline_wells = [well_ for well_ in offline_wells if well_ != well["Label"]] # Remove the well from standby
        else:
            rates[well['Mass Source']] = str(remaining_rate) # if potential rate is higher than limit, do the limit
            remaining_rate = 0.00001
            offline_wells = [well_ for well_ in offline_wells if well_ != well["Label"]] # Remove the well from standby
    return rates, offline_wells


def minimise_water(rate_limit, overridden_wells, offline_wells, rates):
    '''
    FUNCTION NOT IN USE : LOGIC DOES NOT YET WORK
    '''
    # Get CGRs
    sorted_well_WGRs = [[well for well in well_data if well["Label"] == item[0]][0] for item in sorted(reservoir_wgrs.items(), key=lambda item: item[1]) if item[0] not in overridden_wells]

    remaining_rate = rate_limit
    for well in sorted_well_WGRs:
        if remaining_rate == 0.00001:
            if well['Label'] not in offline_wells: offline_wells.append(well['Label']) # Well is on standby if theres still wells to produce but no capacity available
            rates[well['Mass Source']] = '0.00001'
        elif branch_maximum_potential_gas_rates[well["Branch"]] < remaining_rate:
            rates[well['Mass Source']] = str(round(branch_maximum_potential_gas_rates[well["Branch"]], 2)) # Maximise the lowest WGR well (set to max potential)  WARNING: This max potential is only true if other wells are flowing at max potential... (so it can likely do more..)
            remaining_rate = round(remaining_rate - branch_maximum_potential_gas_rates[well["Branch"]], 2) 
            offline_wells = [well_ for well_ in offline_wells if well_ != well["Label"]] # Remove the well from standby
        else:
            rates[well['Mass Source']] = str(remaining_rate) # if potential rate is higher than limit, do the limit
            remaining_rate = 0.00001
            offline_wells = [well_ for well_ in offline_wells if well_ != well["Label"]] # Remove the well from standby
    return rates, offline_wells


def choke_calculation():
    '''
    Calculates the downstream temperature of the chokes assuming an isenthalpic flash
    '''
    for well in well_data:
        fluid_file = well["Fluid"]
        with open(f"{working_location}\\{fluid_file}.tab", "r") as f:
            content = f.readlines()
            pvt_table = [line.split("( ")[1].split(")")[0] for line in content[31:]]
            pvt_dataframe = pd.DataFrame([record.split(', ') for record in pvt_table])
            pvt_dataframe.columns = [item for sublist in [x.split(",") for x in list(pvt_dataframe.iloc[0]) if x] for item in sublist] # tab file columns are bugged
            pvt_dataframe = pvt_dataframe[1:].astype(float)
            
            # Get upstream enthalpy
            pressure = well_FWHPs[well['Label']] # in PA
            temperature = well_FWHTs[well['Label']] # in C

            xx = np.linspace(np.min(pvt_dataframe['PT']), np.max(pvt_dataframe['PT']))
            yy = np.linspace(np.min(pvt_dataframe['TM']), np.max(pvt_dataframe['TM']))
            xx, yy = np.meshgrid(xx, yy)

            enthalpy = scipy.interpolate.griddata((pvt_dataframe['PT'], pvt_dataframe['TM']), pvt_dataframe['HG'], (pressure, temperature))

            # Get downstream Temperature
            well_backpressure = well_backpressures[well['Label']]
            well_choke_ds_temps[well['Label']] = round(scipy.interpolate.griddata((pvt_dataframe['PT'], pvt_dataframe['HG']), pvt_dataframe['TM'], np.array([well_backpressure, enthalpy]))[0], 2)


def calculate_flowing_bottom_hole_pressure(reservoir_pressure, well_prod_index, well_rate):
    return f"{round(float(reservoir_pressure.split(' ')[0]) - (float(well_rate) * 1000000)/ float(well_prod_index), 2)} psig"


def run_sequence(well_rates):
    # Run the discrete wells model to get top hole conditions
    flux.log(f"Day {current_day} - Running Wells Simulation to obtain Top Hole conditons")
    if not os.path.exists(f"{working_location}\\{iteration_name} wells.ppl"):
        wells_change_dict = update_change_dict_wells(well_rates)
        genkey_setup_and_run(wells_change_dict, f"{iteration_name} wells", wells_genkey)
    extract_top_hole_conditions(f"{iteration_name} wells")

    # Run the network model with mass sources to get back pressures (using top hole conditions)
    flux.log(f"Day {current_day} - Running Network Mass Source Simulation to obtain Backpressures at calculated well rates with Top Hole Temperature as initial D/S Choke Temperature")
    if not os.path.exists(f"{working_location}\\{iteration_name} backpressures.ppl"):
        network_mass_sources_change_dict = update_change_dict_network_mass(well_rates)
        genkey_setup_and_run(network_mass_sources_change_dict, f"{iteration_name} backpressures", network_model_mass_source)
    extract_backpressures(f"{iteration_name} backpressures", timestep="first")

    # Calculate choke temperature drop
    flux.log(f"Day {current_day} - Performing Choke calculation using Top Hole conditions and Backpressures to get D/S Choke Temperature")
    choke_calculation()

    # Re-run network model with mass sources and calculated downstream T
    flux.log(f"Day {current_day} - Re-Running Network Mass Source Simulation with calculated D/S Choke Temperature")
    if not os.path.exists(f"{working_location}\\{iteration_name}.ppl"):
        network_mass_sources_change_dict = update_change_dict_network_mass(well_rates)
        genkey_setup_and_run(network_mass_sources_change_dict, f"{iteration_name}", network_model_mass_source)

    # Extract these results (branch gas rates, WGR, CGR, etc.)...
    process_outputs(current_day, iteration_name, timestep="first")


def get_model_branches():
    model_branches = []
    with open(network_model_mass_source, "r") as f:
        lines = [re.sub(r"\s\s", "", x) for x in "".join([x.replace("\\\n", "") for x in f.readlines()]).split("\n")]
        for line in lines:
            if "TYPE=FLOWPATH" in line:
                model_branches.append(re.search(rf'LABEL=[a-zA-Z0-9()"/.,\s\-]+(?![a-zA-Z]*=)', lines[lines.index(line) + 1]).group().split("=")[1].replace("\"", ""))
    return model_branches


def check_production_staging(future_wells, overridden_wells, rate_limit):
    production_staging_df = pd.DataFrame([x.toJSONObj() for x in production_staging])
    rate_limit_staging_df = pd.DataFrame([x.toJSONObj() for x in rate_limit_staging]).sort_values(by=['Day'])
    well_stages = {}
    for well in well_data:
        try:
            well_stages[well['Label']] = production_staging_df[production_staging_df['Well Label'] == well['Label']].sort_values(by=['Day'])
        except: # If a well is not included in the production staging info - it is on "standby" for the full field life (never brought online)
            well_stages[well['Label']] = pd.DataFrame({'Well Label': '', 'Day': '', 'Flow (use -1 for unbound)': ''}) # this is represented by a blank dataframe
    for well in well_stages:
        try:
            current_flow = well_stages[well][well_stages[well]["Day"] <= current_day]['Flow (use -1 for unbound)'].iloc[-1]
        except:
            current_flow = 0 # Well is not online yet, set to zero flow
            if well not in future_wells: future_wells.append(well)
        if current_flow != -1 and not current_flow == 0:
            if well not in overridden_wells.keys(): overridden_wells[well] = current_flow
        elif current_flow == -1: # If the current flow is unbound, take it out of the overridden wells dict and standby wells list
            overridden_wells = {well_: rate for well_, rate in overridden_wells.items() if well_ != well}
            future_wells = [well_ for well_ in future_wells if well_ != well]
        elif current_flow == 0: # If the current flow is 0 (not yet online) only take it out of the overridden wells dict
            overridden_wells = {well_: rate for well_, rate in overridden_wells.items() if well_ != well}
    rate_limit = rate_limit_staging_df[rate_limit_staging_df['Day'] <= current_day]['Rate Limit'].iloc[-1]
    return future_wells, overridden_wells, rate_limit
        

if __name__ == '__main__':
    """
    OLGA Life of Field Script.
    Generates Life of Field Analysis based on defined reservoir pressure and flow limitations.

    @iep.entrypoint

    Parameters
    ----------
    Study Name : string
        Study Name
    Production Logic : string {Maximum Potential, Ratio Production, Maximise Condensate, Minimise Condensate, Minimise Water}
        Production Logic
    Rate Limit : Rate_Limit
        Rate Limit
    Time Step : days
        Time Step in Days
    Reservoir Abandon Rate : MMscf/d
        Reservoir Abandon Rate
    Working Location : string
        Network Path Location
    Production Profile : csv
        Production Profile Data
    Wells : OLGA_Wells
        Well Information
    Full Network Model : genkey
        Full Network Model
    Full Network Mass Source Model : genkey
        Full Network Mass Source Model
    Nework Wells Model : genkey
        Nework Wells Model
    OLGA Path : string
        OLGA executable
    Fluid Files : binary_file
        OLGA Fluid Files
    Export Pipeline : string
        Export Pipeline
    Arrival Facility Label : string
        Arrival Facility Label
    Plant Backpressure : barg
        Plant Backpressure
    Maximum Compressor Suction Pressure : barg
        Maximum Compressor Suction Pressure
    Minimum Compressor Suction Pressure : barg
        Minimum Compressor Suction Pressure

    Returns
    -------
    Life of Field Results : csv
        Life of Field Results
    Choke Calculation Record : csv
        Choke Calculation Record
    Output Genkeys : genkey[]
        Output Genkeys
    """
    flux = IEP()

    # Get Script Inputs
    study_name = flux.get_input("Study Name")
    production_logic = flux.get_input("Production Logic")
    rate_limit_staging = flux.get_input("Rate Limit")["Rate Limit Staging"]
    time_step_days = flux.get_input("Time Step")
    abandon_prod_rate = flux.get_input("Reservoir Abandon Rate")
    network_model_wells = flux.get_input("Full Network Model")
    network_model_mass_source = flux.get_input("Full Network Mass Source Model")
    wells_genkey = flux.get_input("Nework Wells Model")
    working_location = flux.get_input("Working Location")
    production_profile_csv = flux.get_input("Production Profile")
    well_data = flux.get_input("Wells")["Wells"]
    production_staging = flux.get_input("Wells")["Production Staging"]
    OLGA_executable = flux.get_input("OLGA Path")
    fluid_files = flux.get_input("Fluid Files")
    export_pipeline = flux.get_input("Export Pipeline")
    arrival_facility_label = flux.get_input("Arrival Facility Label")
    plant_backpressure = flux.get_input("Plant Backpressure")
    maximum_compressor_suction_pressure = flux.get_input("Maximum Compressor Suction Pressure")
    minimum_compressor_suction_pressure = flux.get_input("Minimum Compressor Suction Pressure")

    flux.log("Inputs Extracted!")
    
    #Convertion Factors
    Sm3_s_to_MMscf_d = 3.0511872
    Sm3_s_to_STB_d = 543440.66
    Sm3_Sm3_to_STB_MMscf = 178107.94
    bar_to_psi = 14.5038
    
    # Adjust for version of OLGA
    OLGA_V, network_model_wells = olga_version_check(OLGA_executable, network_model_wells)

    # Dump Genkey and .tab file
    dump_files(fluid_files)

    # Processing the production profiles
    df_production_profile = pd.read_csv(production_profile_csv, header=None).fillna('')
    df_production_profile.columns = df_production_profile.iloc[0] # Fix columns
    df_production_profile = df_production_profile.iloc[1:, 1:]

    # Creates Records lists used throughout the script
    branch_liqc_record, branch_max_potential_cumulative_gas_production_record, well_FWHPs_record, well_FWHTs_record, well_backpressures_record, well_choke_ds_temps_record, suction_pressure_record, offline_wells, branch_gas_rates_record, branch_oil_rates_record, branch_water_rates_record, time_record, name_record, branch_cumulative_gas_production_record, branch_maximum_potential_gas_rates_record, branch_maximum_potential_condensate_rates_record, branch_maximum_potential_water_rates_record, reservoir_pressures_record = ([] for i in range(18))
    export_pipeline_gas_rate, export_pipeline_oil_rate, export_pipeline_water_rate, export_pipeline_WGR, export_pipeline_CGR = ([] for i in range(5))

    # Loops until abandonment
    current_day = 0
    iteration_name = f"{study_name} day 0"
    overridden_wells = {}
    future_wells = []
    rate_limit = rate_limit_staging[0]["Rate Limit"]

    # Get all branches for LIQC
    liqc_branches = get_model_branches()

    # While ANY well is not offline
    while len(offline_wells) < len(well_data): 
        branch_liqc, well_profiles, well_rates, well_FWHTs, well_FWHPs, well_backpressures, well_choke_ds_temps, branch_gas_rates, branch_cumulative_gas_production, branch_maximum_potential_cumulative_gas_production, branch_maximum_potential_gas_rates, branch_maximum_potential_condensate_rates, branch_maximum_potential_water_rates, reservoir_pressures, reservoir_cgrs, reservoir_wgrs, branch_oil_rates, branch_water_rates = ({} for i in range(18))

        # Check production profiles with current cumulative production
        check_production_profile()

        # Check Production Staging
        future_wells, overridden_wells, rate_limit = check_production_staging(future_wells, overridden_wells, rate_limit)

        flux.log(f"Day {current_day} - Running Network Wells Simulation to obtain maximum potential rates")
        run_maximum_potential(first_run_of_timestep=True)
        compression_check()

        # Wait until all recursions of the max potential function are complete before recording
        record_max_potentials()

        suction_pressure_record.append(round(float(get_current_suction_pressure()[0]), 2))

        # Check if any wells to be abandoned based on potential production rate and reservoir pressure
        offline_wells = abandon_check(offline_wells)

        ############### Logic Switch #################
        if production_logic == "Ratio Production": # RATIO PRODUCTION 
            well_rates = ratio_production(rate_limit, overridden_wells, well_rates, offline_wells, future_wells)               
        elif production_logic == "Maximise Condensate": # MAXIMISE CGR 
            well_rates, offline_wells = optimise_condensate(rate_limit, overridden_wells, offline_wells, well_rates, "max")
        elif production_logic == "Minimise Condensate": # MINIMISE CGR            
            well_rates, offline_wells = optimise_condensate(rate_limit, overridden_wells, offline_wells ,well_rates, "min")
        elif production_logic == "Minimise Water": # MINIMISE WGR                 
            well_rates, offline_wells = minimise_water(rate_limit, overridden_wells, offline_wells, well_rates)
        elif production_logic == "Maximum Potential":
            well_rates = {[well["Mass Source"] for well in well_data if well['Branch'] == branch][0]: rate for branch, rate in branch_maximum_potential_gas_rates.items()}
        
        if production_logic != "Maximum Potential": 
            if sum([value for branch, value in branch_maximum_potential_gas_rates.items() if ([well["Label"] for well in well_data if well['Branch'] == branch][0] not in offline_wells) and ([well["Label"] for well in well_data if well['Branch'] == branch][0] not in future_wells)]) > rate_limit:
                run_sequence(well_rates)
            else: 
                if offline_wells or overridden_wells or future_wells:
                    run_sequence(well_rates)
                else: # dont need to run whole sequence - just becomes max potential
                    # Extract these results (branch gas rates, WGR, CGR, etc.)...
                    process_outputs(current_day, f"{iteration_name} max potential")
        else: 
            if offline_wells or overridden_wells or future_wells:
                run_sequence(well_rates)
            else: # dont need to run whole sequence for max potential logic if all wells online at full
                # Extract these results (branch gas rates, WGR, CGR, etc.)...
                process_outputs(current_day, f"{iteration_name} max potential")

        flux.log('"""""""""""""""""""""""""""""\n\n')
        flux.log("--- Current Reservoir Pressures ---\n\n" + "\n".join([f"{key}: {value} psig" for key, value in reservoir_pressures.items()]) + "\n") 
        flux.log("--- Current Production Rates ---\n\n" + "\n".join(
            [f"{[well['Label'] for well in well_data if well['Branch'] == key][0]}: \
                Gas Rate: {round(value)} MMscf/d (Potential: {round(branch_maximum_potential_gas_rates[key])} MMscf/d), \
                Condensate Rate: {round(value*reservoir_cgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]])} STB/d (Potential: {round(branch_maximum_potential_gas_rates[key]*reservoir_cgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]])} STB/d), \
                Water Rate: {round(value*reservoir_wgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]])} STB/d (Potential: {round(branch_maximum_potential_gas_rates[key]*reservoir_wgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]])} STB/d), \
                " for key, value in branch_gas_rates.items()]) + "\n")
        flux.log(f"Total: Gas Rate: {round(sum(branch_gas_rates.values()))} MMscf/d (Potential: {round(sum(branch_maximum_potential_gas_rates.values()))} MMscf/d), \
            Condensate Rate: {round(sum([value*reservoir_cgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]] for key, value in branch_gas_rates.items()]))} STB/d (Potential: {round(sum([branch_maximum_potential_gas_rates[key]*reservoir_cgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]] for key, value in branch_gas_rates.items()]))} STB/d), \
                Water Rate: {round(sum([value*reservoir_wgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]] for key, value in branch_gas_rates.items()]))} STB/d (Potential: {round(sum([branch_maximum_potential_gas_rates[key]*reservoir_wgrs[[well['Label'] for well in well_data if well['Branch'] == key][0]] for key, value in branch_gas_rates.items()]))} STB/d)\n\n")
        flux.log("--- Current Offline Wells: ---\n\n" + "\n".join([well for well in offline_wells]) + "\n\n")
        flux.log("--- Current Future (yet to online) Wells: ---\n\n" + "\n".join([well for well in future_wells]) + "\n\n")
        flux.log("--- Current Arrival/Suction Pressure: ---\n\n" + f"{round(float(get_current_suction_pressure()[0])*bar_to_psi, 2)} psig / {round(float(get_current_suction_pressure()[0]), 2)} barg" + "\n\n")
        flux.log('"""""""""""""""""""""""""""""')        

        # Iterate
        current_day += time_step_days
        iteration_name = f"{study_name} day {current_day}"

    flux.log("Life of Field Modelling Complete...")

    # Write outputs csv for choke calc
    choke_outputs_file = flux.add_output_file("Choke Calculation Record", f"{working_location}\\Choke Calculations.csv")
    time_df = pd.DataFrame(time_record)
    time_df.columns = ["Day Number"]
    branch_gas_df = pd.DataFrame(branch_gas_rates_record)
    branch_gas_df.columns = [well["Label"] + " Gas Rate (MMscf/d)" for well in well_data]
    branch_gas_df['Total Gas Rate (MMscf/d)'] = branch_gas_df.sum(axis=1)
    well_FWHPs_df = pd.DataFrame(well_FWHPs_record)
    well_FWHPs_df.columns = [key + " UPSTREAM PRESSURE (FWHP) (SIMULATED) (Pa)" for key in well_FWHPs.keys()]
    well_FWHTs_df = pd.DataFrame(well_FWHTs_record)
    well_FWHTs_df.columns = [key + " UPSTREAM TEMPERATURE (FWHT) (SIMULATED) (C)" for key in well_FWHTs.keys()]
    well_backpressures_df = pd.DataFrame(well_backpressures_record)
    well_backpressures_df.columns = [key + " D/S PRESSURE (SIMULATED) (Pa)" for key in well_backpressures.keys()]
    well_choke_ds_temps_df = pd.DataFrame(well_choke_ds_temps_record)
    well_choke_ds_temps_df.columns = [key + " D/S TEMPERATURE (CALCULATED) (C)" for key in well_choke_ds_temps.keys()]
    choke_results = pd.concat([time_df, branch_gas_df, well_FWHPs_df, well_FWHTs_df, well_backpressures_df, well_choke_ds_temps_df], axis=1)
    choke_results.to_csv(choke_outputs_file, index=False)

    # Write outputs csv for the LOF analysis
    lof_outputs_file = flux.add_output_file("Life of Field Results", f"{working_location}\\Life of Field Results.csv")

    name_df = pd.DataFrame(name_record)
    name_df.columns = ["NAME"]

    study_name_df = pd.DataFrame(index=range(len(name_record)), columns=range(1))
    study_name_df.columns = ["LOF Study Name"]
    study_name_df['LOF Study Name'] = study_name

    time_df = pd.DataFrame(time_record)
    time_df.columns = ["Day Number"]

    suction_pressure_df = pd.DataFrame(suction_pressure_record)
    suction_pressure_df.columns = ["Arrival / Suction Pressure (barg)"]

    reservoir_pressures_df = pd.DataFrame(reservoir_pressures_record)
    reservoir_pressures_df.columns = [well["Label"] + " Reservoir Pressure (psig)" for well in well_data]
    
    branch_gas_df = pd.DataFrame(branch_gas_rates_record)
    branch_gas_df.columns = [well["Label"] + " Gas Rate (MMscf/d)" for well in well_data]
    branch_gas_df['Total Gas Rate (MMscf/d)'] = branch_gas_df.sum(axis=1)

    branch_max_potential_branch_gas_df = pd.DataFrame(branch_maximum_potential_gas_rates_record)
    branch_max_potential_branch_gas_df.columns = [well["Label"] + " Max. Potential Gas Rate (MMscf/d)" for well in well_data]
    branch_max_potential_branch_gas_df['Total Max. Potential Gas Rate (MMscf/d)'] = branch_max_potential_branch_gas_df.sum(axis=1)

    branch_condy_rate_df = pd.DataFrame(branch_oil_rates_record)
    branch_condy_rate_df.columns = [well["Label"] + " Condensate Rate (STB/d)" for well in well_data]
    branch_condy_rate_df['Total Condensate Rate (STB/d)'] = branch_condy_rate_df.sum(axis=1)

    branch_max_potential_condy_rate_df = pd.DataFrame(branch_maximum_potential_condensate_rates_record)
    branch_max_potential_condy_rate_df.columns = [well["Label"] + " Max. Potential Condensate Rate (STB/d)" for well in well_data]
    branch_max_potential_condy_rate_df['Total Max. Potential Condensate Rate (STB/d)'] = branch_max_potential_condy_rate_df.sum(axis=1)

    branch_water_rate_df = pd.DataFrame(branch_water_rates_record)
    branch_water_rate_df.columns = [well["Label"] + " Water Rate (STB/d)" for well in well_data]
    branch_water_rate_df['Total Water Rate (STB/d)'] = branch_water_rate_df.sum(axis=1)

    branch_max_potential_water_rate_df = pd.DataFrame(branch_maximum_potential_water_rates_record)
    branch_max_potential_water_rate_df.columns = [well["Label"] + " Max. Potential Water Rate (STB/d)" for well in well_data]
    branch_max_potential_water_rate_df['Total Max. Potential Water Rate (STB/d)'] = branch_max_potential_water_rate_df.sum(axis=1)

    branch_cumulative_gas_production_df = pd.DataFrame(branch_cumulative_gas_production_record)
    branch_cumulative_gas_production_df.columns = [well["Label"] + " Cumulative Gas Production (MMscf)" for well in well_data]
    branch_cumulative_gas_production_df["Total Cumulative Gas Production (MMscf)"] = branch_cumulative_gas_production_df.sum(axis=1)

    branch_max_potential_cumulative_gas_production_df = pd.DataFrame(branch_max_potential_cumulative_gas_production_record)
    branch_max_potential_cumulative_gas_production_df.columns = [well["Label"] + " Max. Potential Cumulative Gas Production (MMscf)" for well in well_data]
    branch_max_potential_cumulative_gas_production_df['Total Max. Potential Cumulative Gas Production (MMscf)'] = branch_max_potential_cumulative_gas_production_df.sum(axis=1)

    branch_liqc_df = pd.DataFrame(branch_liqc_record)
    branch_liqc_df.columns = [branch + " Liquid Content (m3)" for branch in liqc_branches]
    branch_liqc_df['Total Liquid Content (m3)'] = branch_liqc_df.sum(axis=1)

    lof_results = pd.concat([name_df, study_name_df, time_df, suction_pressure_df, reservoir_pressures_df, branch_gas_df, branch_max_potential_branch_gas_df, branch_condy_rate_df, branch_max_potential_condy_rate_df, \
        branch_water_rate_df, branch_max_potential_water_rate_df, branch_cumulative_gas_production_df, branch_max_potential_cumulative_gas_production_df, branch_liqc_df], axis=1)
    
    # Insert blank rows to match .csv format required for post processing
    df_new = pd.DataFrame(index=range(4), columns=lof_results.columns)
    lof_results = pd.concat([df_new, lof_results], axis=0)

    lof_results.to_csv(lof_outputs_file, index=False)

    flux.progress(1)
    flux.success("Script Complete!")
