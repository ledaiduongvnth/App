#===============================================================================
# Configuration table for all Raspberry Pi in system, key = Pi's IP suffix
#===============================================================================
CAM_HK=0 # hikvision
CAM_KB=1 # kbvision

PI_CF_TABLES = {
    'vtnet': {
        # B1 floor
        12: {'cam_ip': 2, 'server': 20, 'roi_translation': (0, 0.15)},
        13: {'cam_ip': 3, 'server': 20, 'roi_translation': (0, 0.15)},

        # 1st floor
        14: {'cam_ip': 6, 'server': 23},
        15: {'cam_ip': 7, 'server': 23},
        16: {'cam_ip': 8, 'server': 24},
        17: {'cam_ip': 9, 'server': 24},
    },
    'qk7': {
        12: {'cam_ip': 2, 'server': 20},
        13: {'cam_ip': 3, 'server': 20},
        14: {'cam_ip': 4, 'server': 21},
        15: {'cam_ip': 5, 'server': 21},
        16: {'cam_ip': 6, 'server': 22},
        17: {'cam_ip': 7, 'server': 22},
    },
    'gvm': {
        25: {'cam_ip': 29, 'server': 35, 'door': 35},
        26: {'cam_ip': 30, 'server': 35, 'door': 35},
        23: {'cam_ip': 33, 'server': 36, 'door': 36},
        24: {'cam_ip': 34, 'server': 36, 'door': 36},
    },
    'crown': {
        # 1st floor
        12: {'cam_ip': 2, 'server': 20, 'door': 26, 'roi_translation': (0, 0.074)},
        13: {'cam_ip': 3, 'server': 20, 'door': 26, 'roi_translation': (0, 0.074)},
        14: {'cam_ip': 4, 'server': 21, 'door': 27, 'roi_translation': (0, 0.074)},
        15: {'cam_ip': 5, 'server': 21, 'door': 27, 'roi_translation': (0, 0.074)},

        # B2 floor side-cam
        16: {'cam_ip': 6, 'server': 22, 'door': 24, 'roi_translation': (-0.09, 0.074), 'roi_l_w_ratio': 0.4},
        17: {'cam_ip': 7, 'server': 22, 'door': 24, 'roi_translation': (0.09, 0.074), 'roi_l_w_ratio': 0.6},
        18: {'cam_ip': 8, 'server': 23, 'door': 25, 'roi_translation': (0.09, 0.074), 'roi_l_w_ratio': 0.6},
        19: {'cam_ip': 9, 'server': 23, 'door': 25, 'roi_translation': (-0.09, 0.074), 'roi_l_w_ratio': 0.4},
    },
    'demo_myanma': {
        # B1 floor
        12: {'cam_ip': 2, 'server': 20, 'roi_translation': (0, 0.05)},
        13: {'cam_ip': 84, 'server': 234, 'roi_translation': (0, 0.05)},
    },
}
