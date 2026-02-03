# -*- coding: utf-8 -*-
"""

This code will create bat file(s) out Genkey files in your specified folder.
If there is already a corresponding .tpl file in that folder, it will skip
that genkey file.
"""

import os
import json

with open('main.json', 'r') as file:
        readjson = json.load(file)

############################ INPUTS ################################
filepath = readjson.get("filepath")
Bat_num = 1
OLGA_path =  readjson.get("OLGA_path")

# Change to target directory
os.chdir(filepath)
#make a list of all the files in that folder 
files= os.listdir(os.getcwd())

#this section will exclude any genkey files which have already been used to make tpl files (provided tpl files are in the same folder)
##############################################################################################################
main_list = os.listdir(filepath)

tplList = []
genkeyList = []

for i in main_list:
    
    if '.genkey' in i:
        genkeyList.append(i)
    if '.tpl' in i:
        tplList.append(i[:-4] +'.genkey')

#Remove base genkey file from list of files to batch
# genkeyList.remove(base_file+'.genkey')

remainder = list(set(genkeyList)-set(tplList))

genkeyFiles = remainder

tot_files = len(genkeyFiles)
chunk_size = round(tot_files/Bat_num +1)
chunks = [genkeyFiles[x:x+chunk_size] for x in range(0, tot_files, chunk_size)]

for i,j in enumerate(chunks):
    #write the commands for bat file
    
    filename = 'Parametric_Batch'+ '_%d'  % (i) + '.txt'
    fl = open (filename,'a')
    
    fl.write('@echo off\npushd \"' + filepath+ '\"' +'\n')

    fl.close()
    
    
    #write entries into batfile
    #Concatenate 
    
    
    ConcatFiles = []
    
    for k in j:
        k = OLGA_path+' '+'"' + k.replace('.genkey','.genkey"')
        ConcatFiles.append(k)
    
    fl = open (filename,'a')
    for i in ConcatFiles:
        fl.write('%s\n'% i)
    fl.close()
        
        
    fl = open (filename,'a')
    fl.write('popd\npause\nexit')
    fl.close()
    
    #turn file into batch file.
    my_file = filename
    base = os.path.splitext(my_file)[0]
    final_file = filename.replace('.txt','.bat')
    
    try:
        os.rename(my_file, base + '.bat')
    except:
        os.remove(final_file)
        os.rename(my_file, base + '.bat')
    
        

