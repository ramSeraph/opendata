"""Indian administrative classes, LGD properties and state-specific naming rules."""

st_himachal = {
    'name': 'Himachal pradesh',
    'suffix': 'Subtehsil',
    'type': 'Subtehsil',
    'wd_id': 'Q123264643',
}
st_haryana = {'name': 'Haryana', 'suffix': 'Subtehsil', 'type': 'Subtehsil', 'wd_id': 'Q123264644'}
state_info = {
    '35': {
        'name': 'Andaman And Nicobar Islands',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987709',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Panchayat Samiti',
    },
    '28': {
        'name': 'Andhra Pradesh',
        'suffix': 'Mandal',
        'type': 'Tehsil',
        'wd_id': 'Q122987710',
        'wd_block_id': 'Q122987710',
        'wd_subdiv_id': 'Q125626445',
        'subdiv_label_suffix': 'revenue division',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Mandal Panchayat',
    },
    '12': {
        'name': 'Arunachal Pradesh',
        'suffix': 'Circle',
        'type': 'Tehsil',
        'long': 'Circle',
        'wd_id': 'Q122987711',
        'wd_div_id': 'Q125907363',
        'divs_in_main_hierarchy': False,
        'dp_suffix': 'Zilla Parishad',
    },
    '18': {
        'name': 'Assam',
        'suffix': 'Circle',
        'type': 'Tehsil',
        'long': 'Circle',
        'wd_id': 'Q122987712',
        'wd_div_id': 'Q125907354',
        'wd_block_id': 'Q123009185',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Anchalik Panchayat',
    },
    '10': {
        'name': 'Bihar',
        'suffix': 'Block',
        'type': 'Block',
        'wd_id': 'Q122987713',
        'wd_div_id': 'Q125907353',
        'wd_subdiv_id': 'Q125631936',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Panchayat Samiti',
    },  # tehsils exist and are called aanchals
    '4': {
        'name': 'Chandigarh',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987714',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Panchayat Samiti',
    },  # TODO: check
    '22': {
        'name': 'Chhattisgarh',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987715',
        'wd_div_id': 'Q125907349',
        'wd_block_id': 'Q123009223',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Janpad Panchayat',
    },  # TODO: check
    '7': {
        'name': 'Delhi',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987716',
        'wd_div_id': 'Q125907356',
    },  # TODO: check
    '30': {
        'name': 'Goa',
        'suffix': 'Taluk',
        'type': 'Tehsil',
        'wd_id': 'Q122987717',
        'dp_suffix': 'Zilla Panchayat',
    },
    '24': {
        'name': 'Gujarat',
        'suffix': 'Taluka',
        'type': 'Tehsil',
        'wd_id': 'Q122987718',
        'wd_subdiv_id': 'Q125923559',
        'dp_suffix': 'District Panchayat',
        'bp_suffix': 'Taluk Panchayat',
    },  # TODO: check
    '6': {
        'name': 'Haryana',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987719',
        'wd_div_id': 'Q125907351',
        'wd_block_id': 'Q126118370',
        'alts': [st_haryana],
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Panchayat Samiti',
    },  # TODO: check
    '2': {
        'name': 'Himachal Pradesh',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987720',
        'wd_div_id': 'Q125907359',
        'divs_in_main_hierarchy': False,
        'alts': [st_himachal],
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Panchayat Samiti',
    },
    '1': {
        'name': 'Jammu And Kashmir',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987721',
        'wd_div_id': 'Q125907352',
        'dp_suffix': 'District Planning and Development Board',
        'bp_suffix': 'Block Development Council',
    },  # TODO: check
    '20': {
        'name': 'Jharkhand',
        'suffix': 'Block',
        'type': 'Block',
        'wd_id': 'Q122987723',
        'wd_subdiv_id': 'Q125919353',
        'wd_div_id': 'Q125907347',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Panchayat Samiti',
    },  # TODO: check
    '29': {
        'name': 'Karnataka',
        'suffix': 'Taluk',
        'type': 'Tehsil',
        'wd_id': 'Q122987724',
        'wd_div_id': 'Q125907360',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Taluka Panchayat',
    },  # TODO: check
    '32': {
        'name': 'Kerala',
        'suffix': 'Taluk',
        'type': 'Tehsil',
        'wd_id': 'Q7680362',
        'wd_subdiv_id': 'Q125627541',
        'subdiv_label_suffix': 'revenue division',
        'dp_suffix': 'District Panchayat',
        'bp_suffix': 'Block Panchayat',
    },  # TODO: check
    '37': {
        'name': 'Ladakh',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987726',
        'wd_div_id': 'Q125907364',
        'divs_in_main_hierarchy': False,
        'dp_suffix': 'District Planning and Development Board',
        'bp_suffix': 'Block Development Council',
    },  # TODO: check
    '31': {
        'name': 'Lakshadweep',
        'suffix': 'Subdivision',
        'type': 'Subdivision',
        'wd_id': 'Q122987727',
        'dp_suffix': 'Zilla Panchayat',
    },
    '23': {
        'name': 'Madhya Pradesh',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987728',
        'wd_div_id': 'Q124669069',
        'wd_block_id': 'Q125750771',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Janpad Panchayat',
    },  # TODO: check
    '27': {
        'name': 'Maharashtra',
        'suffix': 'Taluka',
        'type': 'Tehsil',
        'wd_id': 'Q13119795',
        'wd_div_id': 'Q125907357',
        'wd_subdiv_id': 'Q125918906',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Block Panchayat',
    },  # TODO: check
    '14': {
        'name': 'Manipur',
        'suffix': 'Subdivision',
        'type': 'Subdivision',
        'wd_id': 'Q122987729',
        # no divisions?
        'dp_suffix': 'Zilla Parishad',
    },
    '17': {
        'name': 'Meghalaya',
        'suffix': 'Block',
        'type': 'Block',
        'wd_id': 'Q122987730',
        'wd_div_id': 'Q125907362',
        'divs_in_main_hierarchy': False,
    },  # C. & R. D. Block R is for Rural?
    '15': {
        'name': 'Mizoram',
        'suffix': 'Block',
        'type': 'Block',
        'long': 'Rural Development Block',
        'wd_id': 'Q122987731',
    },  # Rural Development Block
    '13': {
        'name': 'Nagaland',
        'suffix': 'Circle',
        'type': 'Tehsil',
        'wd_id': 'Q122987732',
        'wd_div_id': 'Q125907369',
        'divs_in_main_hierarchy': False,
    },
    '21': {
        'name': 'Odisha',
        'suffix': 'Police Station',
        'label_suffix': 'P.S.',
        'type': 'Police Station',
        'wd_id': 'Q122986857',
        'wd_div_id': 'Q125907355',
        'wd_block_id': 'Q61863384',
        'wd_subdiv_id': 'Q60843390',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Panchayat Samiti',
    },  # Tehsils exist, Police station maps are available in the Census Atlas
    '34': {
        'name': 'Puducherry',
        'suffix': 'Taluk',
        'type': 'Tehsil',
        'wd_id': 'Q122987733',
        'bp_suffix': 'Commune Panchayat',
    },
    '3': {
        'name': 'Punjab',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987734',
        'wd_div_id': 'Q125907365',
        'wd_block_id': 'Q123200469',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Panchayat Samiti',
    },  # TODO: check
    '8': {
        'name': 'Rajasthan',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987735',
        'wd_div_id': 'Q125907350',
        'wd_block_id': 'Q123009239',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Block Panchayat',
    },  # TODO: check
    '11': {
        'name': 'Sikkim',
        'suffix': 'Subdivision',
        'type': 'Subdivision',
        'wd_id': 'Q122956696',
        'dp_suffix': 'Zilla Panchayat',
    },  # revenue circles exist
    '33': {
        'name': 'Tamil Nadu',
        'suffix': 'Taluk',
        'type': 'Tehsil',
        'wd_id': 'Q122987736',
        'wd_block_id': 'Q123009250',
        'wd_subdiv_id': 'Q125626392',
        'subdiv_label_suffix': 'division',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Panchayat Samiti',
    },  # TODO: check
    '36': {
        'name': 'Telangana',
        'suffix': 'Mandal',
        'type': 'Tehsil',
        'wd_id': 'Q122987738',
        'wd_block_id': 'Q122987738',
        'wd_subdiv_id': 'Q125626476',
        'subdiv_label_suffix': 'revenue division',
        'dp_suffix': 'Zilla Parishad',
        'bp_suffix': 'Mandal Panchayat',
    },  # TODO: check
    '38': {
        'name': 'The Dadra And Nagar Haveli And Daman And Diu',
        'suffix': 'Taluk',
        'type': 'Tehsil',
        'wd_id': 'Q122987739',
        'dp_suffix': 'Zilla Parishad',
    },  # TODO: check
    '16': {
        'name': 'Tripura',
        'suffix': 'Subdivision',
        'type': 'Subdivision',
        # "long": "Development Block",
        'wd_id': 'Q126201439',
        'wd_block_id': 'Q122987740',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Block Panchayat',
    },  # Development Block
    '5': {
        'name': 'Uttarakhand',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987741',
        'wd_subdiv_id': 'Q125919325',
        'wd_div_id': 'Q125907368',
        'wd_block_id': 'Q123009294',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Kshetra Panchayat',
    },
    '9': {
        'name': 'Uttar Pradesh',
        'suffix': 'Tehsil',
        'type': 'Tehsil',
        'wd_id': 'Q122987742',
        'wd_div_id': 'Q125907346',
        'wd_block_id': 'Q123009286',
        'wd_sd_id': 'Q125631953',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Kshetra Panchayat',
    },
    '19': {
        'name': 'West Bengal',
        'suffix': 'Block',
        'type': 'Block',
        'wd_id': 'Q122987743',
        'wd_div_id': 'Q5284624',
        'wd_subdiv_id': 'Q13058507',
        'dp_suffix': 'Zilla Panchayat',
        'bp_suffix': 'Panchayat Samiti',
    },
}

SUBDIST_ID = 105626471
TEHSIL_ID = 817477
TEHSIL_INDIA_ID = 7694920
CD_BLOCK_INDIA_ID = 2775236

SUBDIV_ID = 7631016
SUBDIV_REVENUE = 24943410
ALL_SUBDIV_IDS = (
    [SUBDIV_ID, SUBDIV_REVENUE]
    + [int(v['wd_subdiv_id'][1:]) for v in state_info.values() if 'wd_subdiv_id' in v]
    + [int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Subdivision']
)

SUBDIST_IDS = [int(v['wd_id'][1:]) for v in state_info.values()]

SUBTEHSIL_IDS = [123264644, 123264643]

ALL_SUBDIST_IDS = [SUBDIST_ID, TEHSIL_ID, TEHSIL_INDIA_ID] + SUBDIST_IDS + SUBTEHSIL_IDS

ALL_TEHSIL_IDS = [SUBDIST_ID, TEHSIL_ID, TEHSIL_INDIA_ID] + [
    int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Tehsil'
]

ALL_BLOCK_IDS = (
    [CD_BLOCK_INDIA_ID]
    + [int(v['wd_id'][1:]) for v in state_info.values() if v['type'] == 'Block']
    + [int(v['wd_block_id'][1:]) for v in state_info.values() if 'wd_block_id' in v]
)

DIST_COUNCIL_OF_INDIA_ID = 2758248
BLOCK_PANCHAYAT_ID = 4927168

VILLAGE_IN_INDIA_ID = 56436498
CENSUS_TOWN_IN_INDIA_ID = 16830604
CENSUS_TOWN = 587144
ALL_VILLAGE_IDS = [VILLAGE_IN_INDIA_ID, CENSUS_TOWN_IN_INDIA_ID]

P_INSTANCE_OF = 'P31'
P_SUBCLASS_OF = 'P279'
P_REPLACED_BY = 'P1366'
P_DISSOLVED = 'P576'
P_COUNTRY = 'P17'
P_LOCATED_IN = 'P131'
P_COORDINATE_LOCATION = 'P625'
P_COEXTENSIVE_WITH = 'P3403'
P_TERRITORY_OVERLAPS = 'P3179'
P_CONTAINS = 'P150'


P_LGD_LOCAL_BODY_CODE = 'P6425'
P_LGD_STATE_CODE = 'P12747'
P_LGD_DIST_CODE = 'P12746'
P_LGD_SUBDIST_CODE = 'P12748'
P_LGD_BLOCK_CODE = 'P12717'
P_LGD_VILLAGE_CODE = 'P12745'
P_CENSUS_CODE = 'P5578'
P_END_TIME = 'P582'

STATE_ID = 12443800
UT_ID = 467745
INDIA_ID = 668
PAK_ID = 843
DIST_ID = 1149652
DIV_ID = 1230708
ALL_DIV_IDS = [DIV_ID] + [int(v['wd_div_id'][1:]) for v in state_info.values() if 'wd_div_id' in v]
PROPOSED_ENTITY = 64728694
FORMER_ENTITY = 15893266

LGD_URL = 'https://lgdirectory.gov.in/downloadDirectory.do?'
LGD_REF_ITEM = 'Q125923171'
P_STATED_IN = 'P248'
