import os
import xml.etree.ElementTree

count = 0
for f in os.listdir('.'):
	if f.endswith(".xml"):
		with open(f,'r') as file:
			fucked = False
			lines = []
			for line in file:
				lines.append(line)
				if "<von>" in line and ("</von><last>" in line):
					fucked = True
					count += 1
			if fucked:
				print(f)
				with open(f+".alt",'w') as fil:
					for line in lines:
						q = line.replace("<von>","<last>")
						q = q.replace("</von><last>"," ")
						fil.write(q)
					fil.close()
			file.close()

print(count)
