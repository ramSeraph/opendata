from common import is_current_instance_of
from constants import (
    ALL_BLOCK_IDS,
    ALL_DIV_IDS,
    ALL_SUBDIST_IDS,
    ALL_SUBDIV_IDS,
    BLOCK_PANCHAYAT_ID,
    DIST_COUNCIL_OF_INDIA_ID,
    DIST_ID,
    STATE_ID,
    UT_ID,
)


def filter_state(v):
    return is_current_instance_of(v, [ STATE_ID, UT_ID ])

def filter_division(v):
    return is_current_instance_of(v, ALL_DIV_IDS)

def filter_district(v):
    return is_current_instance_of(v, [ DIST_ID ])

def filter_subdivision(v):
    return is_current_instance_of(v, ALL_SUBDIV_IDS)

def filter_subdistrict(v):
    return is_current_instance_of(v, ALL_SUBDIST_IDS)

def filter_block(v):
    return is_current_instance_of(v, ALL_BLOCK_IDS)

def filter_district_panchayat(v):
    return is_current_instance_of(v, [ DIST_COUNCIL_OF_INDIA_ID ])

def filter_block_panchayat(v):
    return is_current_instance_of(v, [ BLOCK_PANCHAYAT_ID ])


