import time
import urllib2
from gbt.ygor import GrailClient
from gbt.ygor.GrailClient import Manager

# 2023-08-08 Added astropy rough (no precession etc) radec-to-altaz transform code
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy import units as u
from astropy.time import Time
# Ignore "dubious year" (and other?) warnings
import warnings
warnings.filterwarnings('ignore', module='astropy._erfa')

BTL_MODE = "BTL_MODE"
MODE1 = "MODE1"

def doing_validate(mgr):
    if isinstance(mgr, Manager):
        mgr = mgr.dev

    # Return True if we are validating.  When validating, GetValue returns 123
    # or an empty string, which is not a valid state.
    cur_state = GetValue(mgr, 'state')
    if cur_state == '123' or cur_state == '':
        return True
    return False


def wait_for_state(mgr, state, timeout=5.0):
    if doing_validate(mgr): return

    if isinstance(mgr, str):
        # TODO Maybe don't hard-code hostname
        grail_client = GrailClient('wind', 18000)
        mgr = grail_client.create_manager(mgr)

    s = "NotInService"
    waited = 0.0

    while s != state and waited < timeout:
        time.sleep(0.5)
        s = mgr.get_value('state')
        waited += 0.5

    # TODO Add info about success/failure
    print 'wait_for_state(%s) waited for %.1f seconds' % (state, waited)

    if s != state:
        return False

    return True


def prepare(mgr, to=30.0):
    if doing_validate(mgr): return

    mgr.prepare()

    print 'prepare waiting for Activating state'
    wait_for_state(mgr, 'Activating', 1.0)
    print 'prepare waiting for Ready state'
    is_ready = wait_for_state(mgr, 'Ready', to)
    print 'prepare done'
    return is_ready


def to_btl_conf(mgr):
    """Sets VEGAS to the BTL configuration: All bank managers deselected,
    and the BTLManager selected and ready.

    mgr: The Vegas Coordinator.
    """
    if doing_validate(mgr): return

    print 'turning off VEGAS banks'
    for i in 'ABCDEFGH':
        mgr.set_value('subsystemSelect,Bank%sMgr' % i, False)
    wait_for_state(mgr, "Ready", 10)

    print 'turning on BTLManager'
    mgr.set_value('subsystemSelect,BTLManager', True)

    is_ready = wait_for_state(mgr, "Ready", 120)
    print 'BTLManager ready == %s' % is_ready
    return is_ready


def set_btl_mode_lowlevel(mgr, mode, active_players="BLP[0-7][0-7]", obs_mode="raw"):
    if doing_validate(mgr): return

    mgr.set_value("mode,25", "BTL_MODE")
    mgr.set_value("btl_mode", mode)
    mgr.set_value("obs_mode,25", obs_mode)
    mgr.set_value("active_players", active_players)
    mgr.set_value("scale_p0", 32*20)
    mgr.set_value("scale_p1", 32*20)
    return prepare(mgr)


def to_vegas_conf(mgr):
    """Sets VEGAS to the BANK configuration: All bank managers selected,
    and the BTLManager deselected.

    mgr: The Vegas Coordinator.

    """
    if doing_validate(mgr): return

    mgr.set_value('subsystemSelect,BTLManager', False)
    wait_for_state(mgr, "Ready", 0.1)

    for i in 'ABCDEFGH':
        mgr.set_value('subsystemSelect,Bank%sMgr' % i, True)
        wait_for_state(mgr, "Ready", 0.1)

    prepare(mgr)
    return wait_for_state(mgr, "Ready", 40)

def get_default_players(btl_mode='CODD_MODE_512_64'):
    active_players = 'BLP[0-7][0-7]'
    if btl_mode == 'CODD_MODE_512':
        active_players = 'BLP0[0-7]'

    elif btl_mode == 'CODD_MODE_512_16':
        active_players = 'BLP[0-1][0-7]'

    elif btl_mode == 'CODD_MODE_512_24':
        active_players = 'BLP[0-2][0-7]'

    elif btl_mode == 'CODD_MODE_512_32':
        active_players = 'BLP[0-3][0-7]'

    elif btl_mode == 'CODD_MODE_512_32_4':
        #active_players = 'BLP[1,3,5,7][0-7]'
        active_players = 'BLP[4-7][0-7]'

    elif btl_mode == 'CODD_MODE_512_56':
        active_players = 'BLP[0-6][0-7]'

    elif btl_mode == 'CODD_MODE_512_64':
        active_players = 'BLP[0-7][0-7]'

    return active_players

def get_players(btl_mode='CODD_MODE_512_64'):
    active_players = 'BLP[0-7][0-7]'
    url = 'http://bl-head/cgi-bin/bl_cgi_dibas_data_mapping.rb?mode=%s' % btl_mode
    try:
      active_players = urllib2.urlopen(url).read()
    except URLError:
      active_players = 'BLP[0-7][0-7]'

    return active_players

def set_btl_mode(btl_mode=None):
    mgr_name = 'VEGAS'
    if doing_validate(mgr_name): return

    # Booleanize btl_mode
    btl_on = bool(btl_mode)

    # TODO Maybe don't hard-code hostname
    grail_client = GrailClient('wind', 18000)
    mgr = grail_client.create_manager(mgr_name)

    if btl_on:
        active_players = get_players(btl_mode)
        to_btl_conf(mgr)
        set_btl_mode_lowlevel(mgr, btl_mode, active_players)
        mgr.conform()
        prepare(mgr, 120)
        print 'BTL mode is set'
        
    else:
        to_vegas_conf(mgr)

def radec_to_azel(ra, dec, t=Time.now()):
    gbo = EarthLocation(lat=38.4*u.deg, lon=-79.8*u.deg, height=808*u.m)
    gboaltaz = AltAz(obstime=t, location=gbo)
    source = SkyCoord(ra*u.hr, dec*u.deg)
    altaz = source.transform_to(gboaltaz)
    return (altaz.az.deg, altaz.alt.deg)
