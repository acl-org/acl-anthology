import csv

FILE = "acl_2022_underline.csv"


with open(file) as f:
   reader = csv.reader(f)
   next(reader)  # Skip header row
   for row in reader:
       # Access by index
       print(row[0])  # First column