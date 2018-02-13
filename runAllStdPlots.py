from std1_percentage_ND import std1Call
from std2_percentage_ttimeUsers import std2Call
from std3_percentage_pathflow import std3Call
from std4_elapsedTime_ND import std4Call
from std5_elapsedTime_enteringVehicles import std5Call
import sys

def printUsageLocal(): 
  print('usage: \n\tpython runAllStdPlots.py directoryName maxEntranceTime')
  print('directoryName: the directory in which the sqlite databases are stored.') 
  print('maxEntranceTime: The maximum allowed entrance time into the network.')
  print('\tIMPORTANT NOTE: You can modify utilities.py to manually rule out unwanted files in the directory.')
  print('\nsystem exiting...')
  sys.exit() 

if __name__ == '__main__': 
  if len(sys.argv) != 3:
    printUsageLocal()
  dirName  = sys.argv[1]
  maxTime  = int(sys.argv[2])
  std1Call(dirName, maxTime)
  std2Call(dirName, maxTime)
  std3Call(dirName, maxTime)
  std4Call(dirName, maxTime)
  std5Call(dirName, maxTime)
