import numpy as np
from scipy.spatial.distance import braycurtis
from scipy.stats import ks_2samp, chisquare
import copy 
from utils import *

adjust_rssi_params = -100, math.e, 2.63
white_list1 = {"EA:23:CD:D2:14:3F", "D4:C4:9C:31:E5:A3", "DF:4F:30:41:5F:15", "D9:CC:B0:17:A8:49", "DA:05:F5:B5:08:4B",
                "D0:4B:6F:D5:85:0A", "E8:85:60:7A:57:5C", "E1:BD:CB:04:65:61", "D0:50:5A:6F:DC:F6", "FF:D2:CD:8A:62:BC"}

white_list = {"C2:BF:7C:A2:CA:0A", "E0:B5:15:E6:C7:E8", "F7:8C:5A:62:37:F7", "CA:13:EA:20:FE:47", "D8:7E:C3:7A:5D:99",
                "E5:90:28:11:B6:2D", "CA:DC:D3:70:50:59", "FD:16:20:18:8C:04", "E7:B0:A7:A3:8A:07", "C3:85:B5:A2:62:66",
                "DD:24:FE:76:E6:EB", "F2:07:77:08:A9:59", "F6:DD:41:B3:18:27", "FA:7B:6B:86:0D:83", "DC:A6:5F:C0:A4:65"}
    

def adjust_rssi_ble(rssi_in):
    min_rssi, exponent, scaler = adjust_rssi_params
    rss_out = []
    if type(rssi_in) is int:
        rssi_in = [rssi_in]
    assert (type(rssi_in) is list), "RSS muste be int or list of ints"

    for rssi_val in rssi_in:
        if rssi_val < 0 and rssi_val > min_rssi:
            positive = rssi_val - min_rssi
            rssi = scaler * pow(-positive/min_rssi, exponent)
        else:
            rssi = 0
        rss_out.append(rssi)
    return rss_out

def precalculate_fingerprints_ble(c): # c is a collection
    """ creates new fields to speed up distance comparisons 
          c.ufingerprint['blerssi'][mac] = average dBm 
    """
    ufingerprint = {}
    ufingerprint['blerssi'] = {}
    for f in c['fingerprints']:
        if not "ble" in f.keys():
            continue
        for mac in f["ble"].keys():
            avg_pow = np.average(f["ble"][mac]['rssi']) # each fingerprint (direction) counts the same
            if not mac in ufingerprint["blerssi"].keys():
                ufingerprint["blerssi"][mac] = [avg_pow] 
            else:
                ufingerprint["blerssi"][mac].append(avg_pow)
    for mac in ufingerprint["blerssi"].keys():
        ufingerprint["blerssi"][mac] = \
            np.average(adjust_rssi_ble(ufingerprint["blerssi"][mac])) #each fingerprint (direction) counts the same
    c['ufingerprint'] = ufingerprint

def merge_fingerprints_ble(flist):
    if len(flist) == 1:
        return flist[0]
    fingerprint = copy.deepcopy(flist[0])
    for f2 in copy.deepcopy(flist[1:]):
        if not "ble" in f2.keys():
            continue
        for mac in f2["ble"].keys():
            if not mac in fingerprint["ble"].keys():
                fingerprint["ble"][mac] = f2["ble"][mac]
            else:
                fingerprint["ble"][mac]['rssi'].extend(f2["ble"][mac]['rssi'])
            fingerprint["ble"][mac]['rssi'].sort()    
    return fingerprint

def compare_fingerprints_ble(c1, c2, simil_method = braycurtis,  selection = 'Average', dif = True):
    # precalculated with average, adjust_rssi  
    ble1 = c1['ufingerprint']['blerssi']
    ble2 = c2['ufingerprint']['blerssi']      

    common_aps = list(set(ble1.keys()) & set(ble2.keys()) & white_list)
    print(common_aps)
    # No APs in common -> similarity = 1
    if not common_aps:
        return 1.66

    #if len(common_aps) * 5 <= len(ble1.keys()): or len(common_aps) < 3:
    #    return 1.0

    aps1 = set(ble1.keys()) - set(common_aps)
    aps2 = set(ble2.keys()) - set(common_aps)
    rssi1 = np.empty(len(common_aps) + len(aps1) + len(aps2), dtype=float)
    rssi2 = np.empty(len(common_aps) + len(aps1) + len(aps2), dtype=float)
    nap = 0

    if selection == 'First':
        for ap in common_aps:
            rssi1.append(ble1[ap]['rssi'][0])
            rssi2.append(ble2[ap]['rssi'][0])

        # Make an average of all RSSI values
    if selection == 'Average':
        for ap in common_aps:
            rssi1[nap] = ble1[ap]
            rssi2[nap] = ble2[ap]
            nap = nap + 1

    if selection == 'Median':
        for ap in common_aps:
            rssi1.append(np.median(adjust_rssi_ble(ble1[ap]['rssi'])))
            rssi2.append(np.median(adjust_rssi_ble(ble2[ap]['rssi'])))

    if selection == 'Mean':
        for ap in common_aps:
            rssi1.append(np.mean(adjust_rssi_ble(ble1[ap]['rssi'])))
            rssi2.append(np.mean(adjust_rssi_ble(ble2[ap]['rssi'])))

    if selection == 'Std':
        for ap in common_aps:
            rssi1.append(np.std(adjust_rssi_ble(ble1[ap]['rssi'])))
            rssi2.append(np.std(adjust_rssi_ble(ble2[ap]['rssi'])))

    if selection == 'Max':
        for ap in common_aps:
            rssi1.append(np.max(adjust_rssi_ble(ble1[ap]['rssi'])))
            rssi2.append(np.max(adjust_rssi_ble(ble2[ap]['rssi'])))

    if selection == 'KS':
        for ap in common_aps:
            _, p = ks_2samp(ble1[ap]['rssi'], ble2[ap]['rssi'])
            rssi1.append(p)
            rssi2.append(1.0)

    if (dif == True) and (selection != 'KS'):
        if len(rssi1) > nap:
            rssi1[nap] = rssi1[0]
            rssi2[nap] = rssi2[0]
        rssi1 = np.diff(rssi1, append=rssi1[0])
        rssi2 = np.diff(rssi2, append=rssi1[0])   


    for ap in aps1:
        rssi1[nap] = 1.0*ble1[ap]
        rssi2[nap] = adjust_rssi_ble([-95.0])[0]
        nap = nap + 1
    for ap in aps2:
        rssi2[nap] = 1.0*ble2[ap]
        rssi1[nap] = adjust_rssi_ble([-95.0])[0]
        nap = nap + 1

    return simil_method(rssi1, rssi2)


def find_most_similar_location(collections, collection, no = 1):
    simil = []
    for c in range(0, len(collections), 1):
        if collections[c] == collection:
            continue
        simil.append((c,(compare_fingerprints(collections[c], collection))))

    simil.sort(key = lambda x: x[1])
    return [v[0] for v in simil[0:no]]

def find_furtherest_2_locations(collections, i_collections):
    result = []
    max_distance = 0
    for c1 in i_collections:
        for c2 in i_collections:
            dist = euclidean([collections[c1]['x'], collections[c1]['y'], collections[c1]['z']], [collections[c2]['x'], collections[c2]['y'], collections[c2]['z']])
            if dist > max_distance:
                result = [c1, c2]


    return result
