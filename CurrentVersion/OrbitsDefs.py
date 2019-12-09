# ORBITS Default values
orbits={}
orbits['OnOffDuration']=120                   # Length of calibration observations in sec
orbits['OnOffDelRA']=0.0                      # Delta RA and Dec, in degrees for calibration OnOff and for Tsys observations
orbits['OnOffDelDec']=1.0
orbits['pulsarDuration']=300                  # length of pulsar observations in sec
orbits['obsDuration']=300                     # length of primary/secondary onbservations in sec
orbits['setTimeLimit']=0.75                   # Approximate length of a full sequence of observations in hours, plus a buffer
orbits['maxMoveTime']=1e10                    # when searching for sources, only use those whose move times are below this limit
orbits['numBreakSources']=999999              # when searching a large catalog, the number of objects that are above the
                                            # horizon within the specified move time that are to be considered.
orbits['solarAvoid']=10                       # solar avoidance radius in deg
orbits['lunarAvoid']=2                        # lunar avoidance radius in deg
orbits['primaryAvoidFWHM']=5                  # radius that secondary sources must lie away from a primary source, in deg.
orbits['tsysDur'] = 15                        # Duration for a Tsys measurement in seconds
orbits['tsysLogFile'] = "/home/groups/btl/ORBITS/logfileTsys.txt"  # Log file for Tsys measurements
orbits['apfLogFile'] = "/home/groups/btl/ORBITS/logfile.txt"       # Log file for APF measurements

#----------------------
#Adding default status of Cal 
Annotation("CALSTATE","CALOFF")

#----------------------
# Fill in orbits dictionary from what cleo returns
def parseCLEO2ORBITS( arr ):
    global orbits
    aa=arr.split()
    for j in range(0,len(aa),2):
        orbits[aa[j]]=aa[j+1]
    print "ORBITS Values:"
    for j in orbits:
        print "\t", j, " = ", orbits[j]

#----------------------
# Fill in dictionary for secondary sources from what cleo returns
def parseSecondaries( arr ):
    global secondarySrcs
    aa=arr.split()
    for j in range(0,len(aa),4):
        secondarySrcs["srcName"+str(j/4)]=aa[j]
        secondarySrcs["srcRA"+str(j/4)]=aa[j+2]
        secondarySrcs["srcDec"+str(j/4)]=aa[j+3]

#----------------------
# Since primary and secondary catalogs are huge, cannot use them directly
# Instead, do everything a catlog would do: create a location object and modify
# the M&C's source name
def obsSource( name, ra, dec, duration ):
    print "Observing ", name, ra, dec, " for ", duration, " seconds"
    SetValues('ScanCoordinator', {'source': name})
    Track(Location("J2000", ra, dec), None, duration)

#----------------------
# Checks if a pointing and Tsys is needed.  If so, do it.
def checkLastPointingTsys(loc):

    global doPnt, orbits, needToBTLConfig

    Slew(loc)

    needToBTLConfig = False

    rslts = popen(["/home/groups/btl/ORBITS/CurrentVersion/isPointingNeeded.tclsh",str(orbits)])
    (needToPoint,pntReason) = rslts.split()
    if orbits['doPnt'] == "1" or needToPoint == "1":
        if orbits['doPnt'] == "1":
            print "Performing the initial pointing"
        else:
            print "Must point.  Reason:", pntReason
        pntFoc(loc)
        print "Must make a Tsys measurement.  Reason: Tsys measurement after every pointing"
        measureTsys()
        needToBTLConfig = True
    orbits['doPnt']="0"

    rslts = popen(["/home/groups/btl/ORBITS/CurrentVersion/isTsysNeeded.tclsh",str(orbits)])
    (needToTsys,reason) = rslts.split()
    if needToTsys == "1":
        print "Must make a Tsys measurement.  Reason:", reason
        measureTsys()
        needToBTLConfig = True

    if needToBTLConfig and orbits['online']:
        print "Reconfiguring using:", orbits['configFile']
        execfile(orbits['configFile'])

        
#----------------------
# Wrapper for an AutoPeak(Focus) for a position near that of objName
def pntFoc( objName ):

    global orbits

    print "Configuring DCR and executing APF"

    saveAtten()
    if orbits['online']:
        ResetConfig()
        Configure(DCRConfig)

    Slew(objName)
    if orbits['doFocus'] == "T":
        print "AutoPeakFocus near", objName, " with min flux of ", float(orbits["peakMinFlux"])
        PubBLHead("Executing AutoPeakFocus")
        AutoPeakFocus(flux=float(orbits["peakMinFlux"]))
    else:
        print "AutoPeak near", objName, " with min flux of ", float(orbits["peakMinFlux"])
        PubBLHead("Executing AutoPeak")
        AutoPeak(flux=float(orbits["peakMinFlux"]))

    restoreAtten()

    if orbits['online']:
        print "Updating pointing logfile"
        p = popen(["/home/groups/btl/ORBITS/CurrentVersion/logTsysPointing.tclsh", 'logfile', orbits['apfLogFile'],str(orbits)])

        Break("Check Pointing",30)

def measureTsys():

    global orbits

    print "Configuring DCR and executing Tsys measurement"
    PubBLHead("Configuring DCR and executing Tsys measurement")

    saveAtten()
    if orbits['online']:
        ResetConfig()
        Configure(DCRConfig)

    Balance()
    SetValues('ScanCoordinator', {'source': 'TSYS_BTL'})
    Track(GetCurrentLocation("AzEl"),None,orbits['tsysDur'],fixedOffset=Offset('J2000', orbits['OnOffDelRA'], orbits['OnOffDelDec'], cosv=True))

    restoreAtten()

    if orbits['online']:
        print "Updating Tsys logfile"
        p = popen(["/home/groups/btl/ORBITS/CurrentVersion/logTsysPointing.tclsh", 'logfile', orbits['tsysLogFile'],str(orbits)])


# Wrapper for calling MILK routines and handling results & errors
def popen( cmnd ):

    global orbits

    orbits['telPos'] = str(GetCurrentLocation("Encoder")).replace(" ","")
    orbits['azElPos'] = str(GetCurrentLocation("AzEl")).replace(" ","")

    cmnd.append('telPos')
    cmnd.append(orbits['telPos'])
    cmnd.append('azElPos')
    cmnd.append(orbits['azElPos'])

    p = subprocess.Popen( cmnd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (rslts, errP) = p.communicate()
    if errP != "":
        print errP
        Break(errP)
    return rslts

# Wrapper for calling MILK routines and handling results & errors
def popenNoOrbits( cmnd ):

    p = subprocess.Popen( cmnd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (rslts, errP) = p.communicate()
    if errP != "":
        print errP
        Break(errP)
    return rslts

#----------------------
# Save all current attenuator values
def saveAtten():
    global ifrAtten, crAtten, pfAtten, orbits

    ifrAtten={}
    crAtten={}
    pfAtten={}

    for i in range(1,9):
        ifrAtten["attenuator," + str(i)]=int(GetValue("IFRack","attenuator," + str(i)))
    for i in range(1,17):
        crAtten["CMAttenuator" + str(i)]=float(GetValue("ConverterRack","CMAttenuator" + str(i)))
    if orbits["rcvr"] == "RcvrPF_2":
        pfAtten["IFChannelXAttenuator"]=float(GetValue("RcvrPF_2","IFChannelXAttenuator"))
        pfAtten["IFChannelYAttenuator"]=float(GetValue("RcvrPF_2","IFChannelYAttenuator"))
    if orbits["rcvr"] == "RcvrPF_1":
        pfAtten["IFChannelAAttenuator"]=float(GetValue("RcvrPF_1","IFChannelAAttenuator"))
        pfAtten["IFChannelBAttenuator"]=float(GetValue("RcvrPF_1","IFChannelBAttenuator"))
        pfAtten["IFChannelCAttenuator"]=float(GetValue("RcvrPF_1","IFChannelCAttenuator"))
        pfAtten["IFChannelDAttenuator"]=float(GetValue("RcvrPF_1","IFChannelDAttenuator"))

#----------------------
# Restore previously saved attenuator values
def restoreAtten():
    global ifrAtten, crAtten, pfAtten, orbits
    SetValues("IFRack", ifrAtten)
    SetValues("ConverterRack", crAtten)
    if orbits["rcvr"] == "RcvrPF_1":
        SetValues("Rcvr_PF1", pfAtten)
    if orbits["rcvr"] == "RcvrPF_2":
        SetValues("Rcvr_PF2", pfAtten)

#----------------------
## Funtions for canary run
def PubBLHead(message):
    if GetLST() is None :
        print "Working offline - not publishing commands to bl-head:"+message 
    else:
        os.system("/users/dmacmaho/local/src/redis-5.0.4-RHEL-6.10/src/redis-cli  -h bl-head publish astrid '" + message + "'")

def SafeSleep(seconds):
    if GetLST() is None :
        print "Working offline - not sleeping..."
    else:
        time.sleep(seconds)
