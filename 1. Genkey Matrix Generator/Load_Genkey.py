import re

# def load_Genkey(genkey, output_genkey, changes_dictionary):
def load_Genkey(genkey, i, working_location, changes_dictionary):
    """Creates a genkey file based on the information in changes_dictionary (dictionary containing the permutation).\n\n

    Args:\n
        genkey (genkey): The base case genkey to be used as the starting point to then search through and change values based on permutation.\n
        i (int): Case identifier (name). This is a number.\n
        working_location (string): The directory to which all the generated genkeys will be stored.\n
        changes_dictionary (dict): Dictionary containing the permutations for the current loop (current genkey).
    """
    for key, value_list in changes_dictionary.items(): # Formats changes dictionary
        for sub_list in value_list:
            for value in sub_list:
                changes_dictionary[key][changes_dictionary[key].index(sub_list)][changes_dictionary[key][changes_dictionary[key].index(sub_list)].index(value)] = str(value)

    # Open the original genkey file (to read from) and a new blank genkey file (to write to)
    with open(genkey, 'r') as original_genkey, \
        open(f"{working_location}\\{i}.genkey", "w+") as f:

        # Read lines from original_genkey file and join lines ending with \ (multi-lines) into single lines
        lines = [re.sub(r"\s\s", "", x) for x in "".join([x.replace("\\\n", "") \
            for x in original_genkey.readlines()]).split("\n")]
        
        # Read through each line and see if any of the variables in the line match the changes_dictionary, and if so make the required replacement
        for line in lines:
            for key, value_list in changes_dictionary.items():
                if key in line:
                    if key == "PROFILEDATA":  # Exception for PROFILEDATA, as the data structure is unique for this entry and only contains the output variables
                        line = line.replace(line.split("=")[1], value_list[0][0])
                    else:
                        # print(value_list[0], value_list[1], value_list[2], value_list[3])
                        change_variables = [(a + "=" + b, c + "=" + d) for a, b, c, d in zip(value_list[0], value_list[1], value_list[2], value_list[3])]
                        for change in change_variables:
                            parameter_to_find = change[0]
                            parameter_to_change = change[1]
                            try:
                                if parameter_to_find == re.sub(r'[",]', "", re.search(rf'{parameter_to_find.split("=")[0]}=[_a-zA-Z0-9()"/.,\s\-]+(?![a-zA-Z]*=)', line).group()): #look for the parameter_to_find in the line (the parameter name to match on)
                                    #check if the parameter_to_find value matches what user is looking for as defined in changes_dictionary (the parameter value to match on)
                                    if parameter_to_change.split("=")[0] in re.sub(r'"', "", line):
                                        #pull out the parameter_name = parameter_value substring from the line
                                        match = re.search(rf'{parameter_to_change.split("=")[0]}=[a-zA-Z0-9()"/.,\s\-]+(?![a-zA-Z]*=)', line).group()
                                        #replace the parameter_value with the new value as defined in the changes_dictionary and format based on parameter type
                                        if parameter_to_change.split("=")[0] == "WALL" or parameter_to_change.split("=")[0] == "LABEL":
                                            line = re.sub(rf'{re.escape(match)}', f'{match.split("=")[0]}="{parameter_to_change.split("=")[1]}",', line)
                                        else:
                                            line = re.sub(rf'{re.escape(match)}', f'{match.split("=")[0]}={parameter_to_change.split("=")[1]},', line)
                            except:
                                pass
            #clean the line up and add a newline character to the end for better readability when written to new genkey file
            line = line[:-1] + "\n" if re.match(r'.+,$', line) else line + "\n"
            f.write(line) #write line to new genkey file
        f.close()
        original_genkey.close()
