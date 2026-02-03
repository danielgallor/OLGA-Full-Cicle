import pandas as pd
import itertools
from Load_Genkey import load_Genkey
import json
from pathlib import Path

import re
import numpy as np

def extract_excel_data(excel_doc, perm_type):
    """Extract the excel input data to a pandas DataFrame.\n\n

    Args:\n
        excel_doc (xlsx): Input excel file containing the permutations to be performed.\n\n

    Returns:\n
        DataFrame: Dataframe containing the permutation information in a python-usable DataFrame format.
    """
    # all_df = pd.read_excel(excel_doc, excel_doc.sheet_names[1:], keep_default_na=False) if perm_type == 'grouped' else pd.read_excel(excel_doc, 0, keep_default_na=False)
    # all_df = {"Matrix": all_df} if not isinstance(all_df, dict) else all_df
    all_df = pd.read_excel(excel_doc, excel_doc.sheet_names, keep_default_na=False) if perm_type == 'grouped' else pd.read_excel(excel_doc, 0, keep_default_na=False)
    all_df = {"Matrix": all_df} if not isinstance(all_df, dict) else all_df
    return all_df

def digest_input(inputs, perm_type):
    """Take the input as a DataFrame and generate three dataframes (df, unitlessDf & permutation_df) based on the selected type of permutation.\n\n

    Args:\n
        inputs (DataFrame): The permutations input data in DataFrame format (output from extract_excel_data function)\n
        perm_type (string): The type of permutation to be peformed (all, rows or matrix). 'all' will permutate all possible combinations.\n
        'rows' will permutate cases as rows in the DataFrame. 'matrix' will permutate rows rows across multiple DataFrames (excel sheets).\n\n

    Returns:\n
        df: A DataFrame containing the cases (permutated values) including units.\n
        unitlessDf: A DataFrame containing the cases (permutated values) without units (for generation of the case matrix csv).\n
        permutation_df: A DataFrame containing the genkey changes (instructions for Load_Genkey.py) to be made for each permutation.
    """
    df_lists, df_lists_unitless, df_header_lists, ListofTuples, ListofTuplesUnitless = ([] for i in range(5))
    permutation_df = pd.DataFrame()
    
    for matrix in inputs:
        matrix_list, matrix_list_unitless, matrix_header_list = ([] for i in range(3))
        permutation_df = pd.concat([permutation_df, inputs[matrix].iloc[0:4,1:]], axis=1)

        if perm_type != 'all':
            for row in inputs[matrix].iloc[4:,1:].to_numpy():
                row = [str(x).replace('\xa0', ' ') for x in row]
                matrix_list.append([f'{a} {b}' if b else a for a, b in zip(list(row), inputs[matrix].iloc[3,1:].to_numpy())])
                matrix_list_unitless.append([a for a in list(row)])  
            df_lists.append(matrix_list)
            df_lists_unitless.append(matrix_list_unitless)
            for row in inputs[matrix].iloc[:4,1:].T.to_numpy():
                matrix_header_list.append(f'{list(row)[1]} {list(row)[2]} ({list(row)[3]})' if row[3] else f'{list(row)[1]} {list(row)[2]}')
            df_header_lists.append(matrix_header_list)
            
        else:
            df_lists = list(map(lambda y: [f'{str(z)} {y[1]}' if y[1] else str(z) for z in y[0] if z != ""], [(a, b) for a, b in zip(inputs[matrix].iloc[4:,1:].T.to_numpy(), inputs[matrix].iloc[3,1:].to_numpy())]))
            df_lists_unitless = list(map(lambda y: [f'{str(z)}' if y[1] else str(z) for z in y[0] if z != ""], [(a, b) for a, b in zip(inputs[matrix].iloc[4:,1:].T.to_numpy(), inputs[matrix].iloc[3,1:].to_numpy())]))
            df_header_lists = [f'{x[1]} {x[2]} ({x[3]})' if x[3] else f'{x[1]} {x[2]}' for x in inputs[matrix].iloc[:4,1:].T.to_numpy()]
    
    if perm_type == 'all':
        for i in itertools.product(*df_lists):
            ListofTuples.append(i)
        for i in itertools.product(*df_lists_unitless):
            ListofTuplesUnitless.append(i)

    elif perm_type == 'rows':
        ListofTuples = list(*df_lists)
        ListofTuplesUnitless = list(*df_lists_unitless)

    elif perm_type == 'grouped':
        for i in itertools.product(*df_lists):
            ListofTuples.append(tuple(itertools.chain.from_iterable(i)))
        for i in itertools.product(*df_lists_unitless):
            ListofTuplesUnitless.append(tuple(itertools.chain.from_iterable(i)))
    
    if perm_type != 'all':
        TuplesHeaders = tuple(itertools.chain.from_iterable([x for x in df_header_lists]))
    else:
        TuplesHeaders = df_header_lists

    df = pd.DataFrame(ListofTuples, columns = TuplesHeaders)
    unitlessDf = pd.DataFrame(ListofTuplesUnitless, columns = TuplesHeaders)

    permutation_df = permutation_df.T.reset_index().replace(np.nan, "")
    permutation_df[permutation_df.columns[0]] = [re.sub(r'\.(\d+)', '', x) for x in permutation_df[permutation_df.columns[0]]]

    permutation_df = pd.concat([permutation_df, unitlessDf.T.reset_index(drop=True)], axis=1)
    name_column = pd.DataFrame(range(len(permutation_df.T)))
    permutation_df = permutation_df.T.reset_index(drop=True)
    permutation_df.columns = [x for x in range(1, len(permutation_df.columns) + 1)]
    permutation_df.insert(0, name_column.columns[0], name_column.values)
    permutation_df = permutation_df.T.replace(np.nan, "")
    permutation_df.iloc[0, 0] = "NAME"
    permutation_df.iloc[0, 1:5] = ''
    permutation_df.iloc[0, 5:] = pd.Series(range(0, len(unitlessDf)))

    return (
        df,
        unitlessDf,
        permutation_df
    )


if __name__ == '__main__':
    """
    Generate genkey matrix.
    Generate genkey matrix based on permutations of user input and inital genkey file.

    @iep.entrypoint

    Parameters
    ----------
    Working Location : string
        Network Working Path
    Base Genkey File : genkey
        Genkey File
    Permutation Inputs : xlsx, optional
        Permutation File
    Case Matrix Inputs : csv, optional
        List of Genkey Cases
    Permutation Type : string {all, rows, grouped}
        Permutation Type

    Returns
    -------
    Case Matrix : csv
        List of Genkey Cases
    """
 
    ############################ INPUTS ################################
    print("Matrix Generator Script started, getting inputs..")

    with open('main.json', 'r') as file:
        readjson = json.load(file)
        
    working_location = readjson.get("Working Location")
    genkey_file =readjson.get("Base Genkey File")
    input_file = readjson.get("Permutation Inputs")
    permutation_type = readjson.get("Permutation Type")

    # Output Matrix to a .csv file
  
    output_case_matrix = Path(f"{working_location}\\case_matrix.csv")
    output_case_matrix.touch(exist_ok=True)

    try:
        inputs = extract_excel_data(pd.ExcelFile(input_file), permutation_type)
        # inputs = pd.DataFrame(inputs['Permutation Inputs'])
        if permutation_type == 'all':
            #do ALL permutation combinations
            df, unitlessDf, permutation_df = digest_input(inputs, 'all')
        elif permutation_type == 'rows':
            #treat rows in the input as cases (links variables together)
            df, unitlessDf, permutation_df = digest_input(inputs, 'rows')
        elif permutation_type == 'grouped': 
            #permutate based on groups of rows rows (permutates groups of rows variables)
            df, unitlessDf, permutation_df = digest_input(inputs, 'grouped')
        
        permutation_df.T.to_csv(output_case_matrix, header=None, index=None)

    except:
        permutation_df = pd.read_csv(readjson.get("Case Matrix Inputs"), header=None).T.replace(np.nan, "")
        permutation_df.T.to_csv(output_case_matrix, index=None, header=None)

    print('Progress 50%')
        
    print(f"Case matrix produced, csv name is : {output_case_matrix}")
    print('Progress 60%')

    changes_dictionary = {}
    for i in range(5, 5 + len(permutation_df.columns[5:])):
        for row in permutation_df.to_numpy():
            if row[0] == "NAME":
                continue
            if row[0] == "PROFILEDATA":
                changes_dictionary[row[0]] = [
                    [df.loc[i, row[2] + " " + row[3]]]
                ]
            else:
                try:
                    changes_dictionary[row[0]][0].append(row[1])
                    changes_dictionary[row[0]][1].append(row[2])
                    changes_dictionary[row[0]][2].append(row[3])
                    changes_dictionary[row[0]][3].append(row[i] if (str(row[4]) == 'nan' or str(row[4]) == "") else row[i] + " " + str(row[4]))
                except:
                    changes_dictionary[row[0]] = [
                        [row[1]],
                        [row[2]],
                        [row[3]],
                        [row[i] if (str(row[4]) == 'nan' or str(row[4]) == "") else row[i] + " " + str(row[4])]
                    ]
        load_Genkey(genkey_file, i + 0 - 5, working_location, changes_dictionary)
        print(f"Genkey produced, genkey name is : {i - 5}.genkey")
        changes_dictionary = {}
    
    print('Progress 100%')
    
