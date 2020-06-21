
import os
import sys
import subprocess
def execute_unix(inputcommand):
    p = subprocess.Popen(inputcommand, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    return output

for i in range(5,121):
    s = "sudo rm -r gps-history-f"+str(i)+".txt"
    execute_unix(s)
