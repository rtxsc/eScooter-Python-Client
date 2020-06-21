
import os
import sys
import subprocess
def execute_unix(inputcommand):
    p = subprocess.Popen(inputcommand, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    return output

for i in range(1,8+1):
    # s = "sudo rm -r data"+str(i)+".txt"
    s = "sudo rm -r geojson"+str(i)+".txt"

    execute_unix(s)
