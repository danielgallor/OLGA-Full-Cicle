# Introduction 
For OLGA parametric studies, once a collection of genkey files has been written they need to be added to a batch file (.bat) so that they can be run autonomously.

This program finds genkey files in a folder and adds them to a user selected number of batch files.

If it finds a tpl file with the same name as the genkey file inside the folder, it skips adding that genkey to the batch.

# Tutorial: Getting Started

**1. Required files**

You must have already pip intalled xgc

To begin using this script, download the following files to your local drive:
- OLGA_Batch_Generator.py
- OLGA_Batch_Generator.json

You will also need:
- A folder with genkey files inside it.

As an example, follow the steps in the Readme for Genkey_Matrix_Generator to create a folder with genkey files in it.

**2. Input Data**

To add inputs into the calculation, open *OLGA_Batch_Generator.json*.
You will find the following code:

        { 
        "filepath":,
        "base_genkey_file": ,
        "Bat_num": ,
        "OLGA_path": "call \"\""

        }

This json formatting makes use of a dictionary structure {key:value} to take inputs in.

Each input key has the following meaning:


**filepath**
- This is the filepath where your genkey files are. It does not need to be the same location as the OLGA_Batch_Generator python script.
- Note: when entering a file path into a json file, make sure to use two back slashes instead of one. e.g:

        file_path": "C:\\Users\\username\\python"

**base_genkey_file**
- This is the name of the base genkey used in your study.
- This input is needed to exclude the base genkey file from the created batch files.
- it will also be used to name your batch files.
- Note: Do not include the ".genkey" file extension here. e.g:

        "base_genkey_file": "Example"

**Bat_num**
- This specifies the number of batch files to create. The genkey files will be distributed equally between the batch files.
- Note: To run batch files concurrently, one OLGA licenses is required per batch.
- E.g 

        "Bat_num": 2



**"OLGA_path"**
- This is the path of the OLGA program executable file which will run the genkey.
- This is specific to the user as the location of the OLGA install can differ between users.
- This is also specific to the version of OLGA which the user wants to run. The OLGA_path for OLGA 2015 and OLGA 2018 will differ.
- Note: insert the path after the first backslah, making sure to change any single slashes within your copied file path to double slashes. e.g.:

        "OLGA_path": "call \"C:\\Program Files (x86)\\Schlumberger\\OLGA 2015.2.1\\OlgaExecutables\\OLGA-2015.2.1.exe\""

C:\\Program Files\\Schlumberger\\OLGA 2020.2.0\\OlgaExecutables\\OLGA-2020.2.0.exe    **replace for 2020 OLGA



**3. Running the program**

Once all necessary inputs have been made, try running the program.

You should see the following files created in your folder:

![](%2FReadme_images%2Fbatch_created.PNG)

if you right click and select edit on the first batch file, you should see the following:

![](%2FReadme_images%2FBat_file_details.PNG)


