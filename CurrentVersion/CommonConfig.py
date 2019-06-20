#-------------------------------------------------------------------
# Everything one needs to do to configure BTLManager, switching signals, etc for
# every receiver.  Requires that the calling script has provided values for:
#   btlMode
#   config_g
#   oreo(doBalance)
# Defines the following Configure variables that can be used in the calling astrid scripts:
#   configNoiseOn
#   configNoiseOff

# Dictionary to translate a mode string to an active_player string?
playerDict = {
        'CODD_MODE_512':      'BLP0[0-7]',
        'CODD_MODE_512_16':   'BLP[0-1][0-7]',
        'CODD_MODE_512_24':   'BLP[0-2][0-7]',
        'CODD_MODE_512_32':   'BLP[0-3][0-7]',
        'CODD_MODE_512_32_4': 'BLP[4-7][0-7]',
        'CODD_MODE_512_64':   'BLP[0-7][0-7]'
    }

# To turn on and off noise flickering, call Configure on the following:
configNoiseOn="""
swmode = 'tp'
"""

configNoiseOff="""
swmode = 'tp_nocal'
"""

# Initial configure
ResetConfig()
Configure(config_g)

# Do Balance()?
if 'doBalance' in oreo and oreo['doBalance']:
    Balance()

# Modify VEGAS parameters.  Turn on the BTLManager.  Unselect VEGAS banks
for i in 'ABCDEFGH':
    SetValues("VEGAS", {'subsystemSelect,Bank%sMgr' % i: 0})
SetValues("VEGAS", {
    'subsystemSelect,BTLManager': 1,
    'mode,9': "BTL_MODE",
    'btl_mode': btlMode,
    'active_players' : playerDict[btlMode], 
    'scale_p0': 20,
    'scale_p1': 20
})

# SetValues("VEGAS", {'state': 'prepare'})
# SetValues("BTLManager", {'state': 'on'})

# Use DCR as switching signal master
SetValues("SwitchingSignalSelector",{
    "selCal": "Source_0",
    "selSigRef": "Source_0",
    "selAdvSigRef": "Source_0",
    "selBlanking": "Source_0"
})
SetValues("ScanCoordinator", {
    "subsystemSelect,DCR":"1",
    "switching_signals_master": "DCR"
})

