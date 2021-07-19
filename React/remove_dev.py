import os
import re
import subprocess
from pprint import pprint
directory_views = os.listdir('./src/views')
directory_containers = os.listdir('./src/containers')
files = ['./src/App.js']
for file in directory_views:
    if file.endswith(".js"):
        files.append('./src/views/' + file)
for file in directory_containers:
    if file.endswith(".js"):
        files.append('./src/containers/' + file)
pprint(files)
for file in files:
    open_file = open(file,'r')
    read_file = open_file.read()
    regex = re.compile('http://10.0.0.9')
    read_file = regex.sub('', read_file)
    write_file = open(file, 'w')
    write_file.write(read_file)
subprocess.run(["npm", "run", "build"])