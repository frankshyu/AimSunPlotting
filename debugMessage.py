def printObjFiles(f, debug):
  if debug == 'true':
    print('file names are...')
    for filename in f:
      print(filename)

def printTraverseResults(percent, appTTime, nonAppTTime, debug):
  if debug == 'true':
    print('the results of travering multiple databases are:')
    print('percentage:')
    print percent
    print('appTTime')
    print appTTime
    print('nonAppTTime')
    print nonAppTTime

def printTraverseSingleDB(percentage, appTTime, numApp, nonAppTTime, numNonApp, totalTTime, numVeh, debug):
  if debug == 'true':
    print('the percentage of App users is:')
    print(percentage)
    print('the mean app travel time is:')
    print(appTTime)
    print('the number of app users is:')
    print(numApp)
    print('the mean non-app travel time is:')
    print(nonAppTTime)
    print('the number of non-app users is:')
    print(numNonApp)
    print('the mean travel time is:')
    print(totalTTime)
    print('the number of all vehicles is:')
    print(numVeh)
    print('===================================================')
