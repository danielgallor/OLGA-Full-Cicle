import sys
import re
import pandas as pd
from pathlib import Path

#Convert a 2015 genkey file to 2018 compatible version if user has OLGA 2018 (i.e. change keywords, change wells to reservoir contacts etc.)
def transform_2015_to_2018(genkey):
    with open(genkey) as currentgenkeyMain, open(
        f"{Path(currentgenkeyMain).stem} base_genkey_OLGA_2018.genkey", "w"
    ) as outputgenkey:
        # Read lines from original_genkey file and join lines ending with \ (multi-lines) into single lines
        lines = [re.sub(r"\s\s", "", x) for x in "".join([x.replace("\\\n", "") \
            for x in currentgenkeyMain.readlines()]).split("\n")]
        newLines = []
        library_additions = []
        prodi = ""
        phase = ""
        pipe = ""
        section = ""
        # Replace 2015 keywords with 2018 keywords
        for line in lines:
            if len(line):
                if line.split()[0] == "WELL":
                    line = line.replace(" WELL ", " RESERVOIRCONTACT ") 
                    line = line.replace(" RESPRESSURE=", " PRESSURE=") 
                    line = line.replace(" RESTEMPERATURE=", " TEMPERATURE=") 
                    try:
                        old_label = re.match(r'.+LABEL=[a-zA-Z0-9]+[,\s]?', line).group().split("LABEL=")[1].replace(",","")
                        line = re.sub(r'LABEL=[a-zA-Z0-9]+[,\s]?', f"LABEL=\"{old_label}\",", line)
                    except:
                        pass
                    try:
                        old_prodoption = re.match(r'.+PRODOPTION=[a-zA-Z]+[,\s]?', line).group().split("PRODOPTION=")[1].replace(",","")
                        line = re.sub(r'PRODOPTION=[a-zA-Z]+[,\s]?', f"PRODIPR=\"PROD-{old_prodoption}\",", line)
                        library_additions.append(f"PROD-{old_prodoption}")
                    except:
                        pass
                    try:
                        old_injoption = re.match(r'.+INJOPTION=[a-zA-Z]+[,\s]?', line).group().split("INJOPTION=")[1].replace(",","")
                        line = re.sub(r'INJOPTION=[a-zA-Z]+[,\s]?', f"INJIPR=\"INJ-{old_injoption}\",", line)
                        library_additions.append(f"INJ-{old_injoption}")
                    except:
                        pass
                    line = re.sub(r'ISOTHERMAL=[a-zA-Z]+[,\s]?', "", line) 
                    try: 
                        pipe = re.match(r'.+PIPE=[a-zA-Z\-"0-9]+[,\s]?', line).group().split("PIPE=")[1].replace(",","")
                    except:
                        pass
                    line = re.sub(r'PIPE=[a-zA-Z\-"0-9]+[,\s]?', "", line)
                    try: 
                        section = re.match(r'.+SECTION=[0-9]+[,\s]?', line).group().split("SECTION=")[1].replace(",","")
                    except:
                        pass
                    line = re.sub(r'SECTION=[0-9]+[,\s]?', "", line)
                    line = re.sub(r'INJECTIVITY=[0-9.\sa-zA-Z/]+[,\s]?', "", line) 
                    try:
                        phase = re.match(r'.+PHASE=[a-zA-Z]+[,\s]?', line).group().split("PHASE=")[1].replace(",","")
                    except:
                        pass
                    line = re.sub(r'PHASE=[a-zA-Z]+[,\s]?', "", line) 
                    try:
                        prodi = re.match(r'.+PRODI=[0-9.\sa-zA-Z/]+[,\s]?', line).group().split("PRODI=")[1].replace(",","")
                    except:
                        pass
                    line = re.sub(r'PRODI=[0-9.\sa-zA-Z/]+[,\s]?', "", line)
                    line = line.rstrip() + f" POSITION=\"{old_label} - POS\"" + f"\n POSITION LABEL=\"{old_label} - POS\", PIPE={pipe}, SECTION={section}\n"             
            line = line.rstrip()[:-1] + "\n" if re.match(r'.+,$', line.rstrip()) else line.rstrip() + "\n"   
            newLines.append(line)

        #Create new library keywords for the old wells
        for line in newLines:
            if "Library keywords" in line:
                for library_addition in list(set(library_additions)):
                    well_type = library_addition.split("-")[0]
                    prodi = prodi.replace("-", "") if well_type == "PROD" else "-" + prodi
                    keyword = library_addition.split("-")[1]
                    newLines[newLines.index(line) + 1] = f"{newLines[newLines.index(line) + 1]}{keyword} LABEL=\"{library_addition}\", MODELOPTION=VOLUME, PI={prodi}, PHASE={phase}\n"

        outputgenkey.writelines(newLines)
        return outputgenkey

def update_inputs(input_file):
    inputs_df = pd.read_excel(input_file, keep_default_na=False)
    inputs_df.replace(to_replace=r'WELL', value='RESERVOIRCONTACT', regex=True, inplace=True)
    inputs_df.replace(to_replace=r'RESPRESSURE', value='PRESSURE', regex=True, inplace=True)
    inputs_df.replace(to_replace=r'RESTEMPERATURE', value='TEMPERATURE', regex=True, inplace=True)
    return inputs_df

if __name__ == "__main__":
    transform_2015_to_2018(sys.argv[1], sys.argv[2])
