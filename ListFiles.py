import os
import csv
 
def list_files(directory):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_list.append(os.path.join(root, file))
    return file_list
 
files = list_files('X:\\Divisions\\Production Assurance')
 
# Write the list to a CSV file
with open('C:\\MLB Python\\Files List_Updated.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['File Path'])
    for file_path in files:
        writer.writerow([file_path])