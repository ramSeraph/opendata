import json
import csv
import glob
import copy
from datetime import datetime
from pprint import pprint

# TODO: correct names

all_errors = {}
def report_validation_error(desc, print_info, save_info):
    print(print_info)
    if len(save_info) == 3:
        print(save_info[1])

    if desc not in all_errors:
        all_errors[desc] = []
    all_errors[desc].append(save_info)


    

parsing_phase = "START"
def mark_phase(phase, log):
    global parsing_phase
    parsing_phase = phase
    print(log)


def get_latest_folder():
    filenames = glob.glob('data/raw/*/')
    valid_filenames = []
    for filename in filenames:
        parts = filename.split('/')
        try:
            datetime_object = datetime.strptime(parts[-2], '%d%b%Y')
            valid_filenames.append((filename, datetime_object))
        except:
            pass
    valid_filenames.sort(key=lambda x:x[1])
    valid_filenames = [ x[0] for x in valid_filenames ]
    input_folder = valid_filenames[-1]
    return input_folder



def parse_states_file(input_folder, all_info, all_info_by_code):
    state_filename = '{}/states.csv'.format(input_folder)
    with open(state_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        for r in reader:
            state_name = r['State Name(In English)']
            state_code = r['State Code']
            info = {
                'name_l': r['State Name (In Local)'],
                'version': r['State Version'],
                'census2001_code': r['Census 2001 Code'],
                'census2011_code': r['Census 2011 Code'],
                'type': r['State or UT']
            }
            if state_name in all_info:
                prev = all_info[state_name]
                report_validation_error('state name repeat in state file',
                                        '{} repeated in state file, prev: {}'.format(state_name, prev),
                                        (state_filename, r))
                continue
            all_info[state_name] = info
            by_code_info = copy.copy(info)
            info['code'] = state_code
            by_code_info['name'] = state_name
            if state_code in all_info_by_code:
                prev = all_info_by_code[state_code]
                report_validation_error('state code repeat in state file',
                                        '{} repeated in state file, prev: {}'.format(state_code, prev),
                                        (state_filename, r))
                continue
            all_info_by_code[state_code] = by_code_info



#TODO: get district versions
def parse_dists_file(input_folder, all_info, all_info_by_code, hierarchies):
    dist_filename = '{}/districts.csv'.format(input_folder)
    with open(dist_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        #{'District Code': '317', 'District Name(In English)': 'MEDINIPUR EAST', 'State Code': '19', 'State Name (In English)': 'WEST BENGAL', 'Census 2001 Code': '15', 'Census 2011 Code': '345'}
        for r in reader:
            dist_name  = r['District Name(In English)']
            state_name = r['State Name (In English)']
            state_code = r['State Code']
            dist_code  = r['District Code']
            #TODO: check census 2011 codes
            info  = {
                'census2001_code': r['Census 2001 Code'],
                'census2011_code': r['Census 2011 Code'],
            }
            if state_code not in all_info_by_code:
                report_validation_error('statecode invalid in dist file parsing',
                                        '{} for {} in dist file is invalid'.format(state_code, dist_name),
                                        (dist_filename, r))
                continue
            state_info_by_code = all_info_by_code[state_code]
            if state_name not in all_info:
                report_validation_error('statename invalid in dist file parsing',
                                        '{} for {} in dist file is invalid'.format(state_name, dist_name),
                                        (dist_filename, r))
                continue
            state_info = all_info[state_name]
            if 'districts' not in state_info_by_code:
                state_info_by_code['districts'] = {}
            if 'districts' not in state_info:
                state_info['districts'] = {}

            if dist_name in state_info['districts']:
                prev = state_info['districts'][dist_name]
                report_validation_error('district name repeated in district file parsing',
                                        '{} for {} is repeated in district file, prev: {}'.format(dist_name, state_name, prev),
                                        (dist_filename, r, prev))
                continue
            state_info['districts'][dist_name] = info
            by_code_info = copy.copy(info)
            info['code'] = dist_code
            by_code_info['name'] = dist_name

            if dist_code in state_info_by_code['districts']:
                prev = state_info_by_code['districts'][dist_code]
                report_validation_error('district code repeated in district file parsing',
                                        '{} for {} is repeated in district file, prev: {}'.format(dist_code, state_name, prev),
                                        (dist_filename, r, prev))
                continue

            state_info_by_code['districts'][dist_code] = by_code_info
            if dist_code in hierarchies['districts']:
                prev = hierarchies['districts'][dist_code]
                report_validation_error('district code global repeat in district file parsing',
                                        '{} for {} is repeated, prev: {}'.format(dist_code, state_name, prev),
                                        (dist_filename, r, prev))
                continue
            hierarchies['districts'][dist_code] = [state_code]


def correct_subdist_record(r, corrections):
    key = corrections['key']
    value = r[key]
    if value in corrections['edit']:
        changes = corrections['edit'][value]['changes']
        r.update(changes)



def parse_subdists_file(input_folder, all_info, all_info_by_code, hierarchies):
    subdist_filename = '{}/subdistricts.csv'.format(input_folder)
    subdist_corrections_filename = 'data/corrections/subdistricts.json'
    with open(subdist_corrections_filename) as f:
        corrections = json.load(f)

    with open(subdist_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        #{'Sub District Code': '1695', 'Sub District Version': '4', 'Sub District Name ': 'Ziro HQ', 'District Code': '236', 'Census 2001 Code': '0', 'Census 2011 Code': '01695'}
        for r in reader:
            correct_subdist_record(r, corrections)
            subdist_name = r['Sub District Name ']
            subdist_code = r['Sub District Code']
            dist_code = r['District Code']
            info = {
                'census2001_code': r['Census 2001 Code'],
                'census2011_code': r['Census 2011 Code'],
                'version'        : r['Sub District Version']
            }
            if dist_code not in hierarchies['districts']:
                report_validation_error('distcode invalid in subdist file parsing',
                                        '{} for {} in subdist file is invalid'.format(dist_code, subdist_name),
                                        (subdist_filename, r))
                continue
             
            state_code = hierarchies['districts'][dist_code][0]
            dist_info_by_code = all_info_by_code[state_code]['districts'][dist_code]
            dist_name = dist_info_by_code['name']
            state_name = all_info_by_code[state_code]['name']
            dist_info = all_info[state_name]['districts'][dist_name]
            if 'subdistricts' not in dist_info_by_code:
                dist_info_by_code['subdistricts'] = {}
            if 'subdistricts' not in dist_info:
                dist_info['subdistricts'] = {}

            if subdist_name in dist_info['subdistricts']:
                prev = dist_info['subdistricts'][subdist_name]
                if prev['code'] != subdist_code:
                    report_validation_error('subdistrict name repeated in subdistrict file parsing',
                                            '{} for {}, {} is repeated in subdistrict file, prev: {}'.format(subdist_name, dist_name, state_name, prev),
                                            (subdist_filename, r, prev))
                    continue
                else:
                    print('duplicate entry for subdist {} in dist {}, state {}'.format(subdist_name, dist_name, state_name))
            dist_info['subdistricts'][subdist_name] = info
            by_code_info = copy.copy(info)
            info['code'] = subdist_code
            by_code_info['name'] = subdist_name
            if subdist_code in dist_info_by_code['subdistricts']:
                prev = dist_info_by_code['subdistricts'][subdist_code]
                report_validation_error('subdistrict code repeated in subdistrict file parsing',
                                        '{} for {} is repeated in subdistrict file, prev: {}'.format(subdist_code, dist_name, prev),
                                        (subdist_filename, r, prev))
                continue
            dist_info_by_code['subdistricts'][subdist_code] = by_code_info

            if subdist_code in hierarchies['subdistricts']:
                prev = hierarchies['subdistricts'][subdist_code]
                report_validation_error('subdistrict code global repeat in subdistrict file parsing',
                                        '{} for {}, {} is repeated, prev: {}'.format(dist_code, dist_name, state_name, prev),
                                        (subdist_filename, r, prev))
                continue
            hierarchies['subdistricts'][subdist_code] = [state_code, dist_code]


def correct_block_record(r, corrections):
    key = corrections['key']
    value = r[key]
    if value in corrections['edit']:
        changes = corrections['edit'][value]['changes']
        r.update(changes)


def block_file_gen(reader, corrections):
    key = corrections['key']
    for r in reader:
        if r[key] in corrections['del']:
            continue
        if r[key] in corrections['edit']:
            changes = corrections['edit'][r[key]]['changes']
            r.update(changes)
        yield r
    additions = corrections['add']
    for addition in additions:
        yield addition['entry']
    


def parse_blocks_file(input_folder, all_info, all_info_by_code, hierarchies):
    block_filename = '{}/blocks.csv'.format(input_folder)
    block_corrections_filename = 'data/corrections/blocks.json'
    with open(block_corrections_filename) as f:
        corrections = json.load(f)

    with open(block_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        #{'S.No.': '7219', 'State Code': '19', 'State Name          (In English)': 'WEST BENGAL', 'District Code': '321', 'District Name         (In English)               ': 'PURULIA', '  Block Code': '3060', 'Block Version': '1', 'Block Name                    (In English) ': 'PURULIA-II'}
        for r in iter(block_file_gen(reader, corrections)):
            block_name = r['Block Name                    (In English) ']
            block_code = r['  Block Code']
            dist_code  = r['District Code']
            dist_name  = r['District Name         (In English)               ']
            state_name = r['State Name          (In English)']
            state_code = r['State Code']
            info = {
                'version' : r['Block Version']
            }
            if dist_code not in hierarchies['districts']:
                report_validation_error('distcode invalid in block file parsing',
                                        '{} for {} in block file is invalid'.format(dist_code, block_name),
                                        (block_filename, r))
                continue
             
            state_code_known = hierarchies['districts'][dist_code][0]
            if state_code_known != state_code:
                report_validation_error('state code mismatch in block file parsing',
                                        '{} for {} in block file doesnt match existing {}'.format(state_code, block_name, state_code_known),
                                        (block_filename, r))
                continue

            state_name_known = all_info_by_code[state_code]['name']
            if state_name_known != state_name:
                report_validation_error('state name mismatch in block file parsing',
                                        '{} for {} in block file doesnt match existing {}'.format(state_name, block_name, state_name_known),
                                        (block_filename, r))
                continue

            dist_info_by_code = all_info_by_code[state_code]['districts'][dist_code]
            dist_name_known = dist_info_by_code['name']
            if dist_name_known != dist_name:
                report_validation_error('dist name mismatch in block file parsing',
                                        '{} for {} in block file doesnt match existing {}'.format(dist_name, block_name, dist_name_known),
                                        (block_filename, r))
                continue


            dist_info = all_info[state_name]['districts'][dist_name]
            if 'blocks' not in dist_info_by_code:
                dist_info_by_code['blocks'] = {}
            if 'blocks' not in dist_info:
                dist_info['blocks'] = {}

            if block_name in dist_info['blocks']:
                prev = dist_info['blocks'][block_name]
                report_validation_error('block name repeated in block file parsing',
                                        '{} for {} is repeated in block file, prev: {}'.format(block_name, dist_name, prev),
                                        (block_filename, r, prev))
                continue
            dist_info['blocks'][block_name] = info
            by_code_info = copy.copy(info)
            info['code'] = block_code
            by_code_info['name'] = block_name

            if block_code in dist_info_by_code['blocks']:
                prev = dist_info_by_code['blocks'][block_code]
                report_validation_error('block code repeated in block file parsing',
                                        '{} for {} is repeated in block file, prev: {}'.format(block_code, dist_name, prev),
                                        (block_filename, r, prev))
                continue
            dist_info_by_code['blocks'][block_code] = by_code_info

            # N.B. blocks can cross district boundaries?
            # Here is looking at which ever toddler decided to set up ASSAM boundaries
            if block_code not in hierarchies['blocks']:
                hierarchies['blocks'][block_code] = []
            hierarchies['blocks'][block_code].append([state_code, dist_code])


def parse_villages_file(input_folder, all_info, all_info_by_code, hierarchies):
    village_filename = '{}/villages.csv'.format(input_folder)
    with open(village_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        for r in reader:
            # {'S.No.': '356855', 'State Code': '2', 'State Name (In English)': 'HIMACHAL PRADESH', 'District Code': '25', 'District Name (In English)': 'SOLAN', 'Sub-District Code': '166', 'Sub-District Name (In English)': 'Kandaghat', 'Village Code': '22455', 'Village Version': '1', 'Village Name (In Englsih)': 'Chohra (476)', 'Village Name (In Local)': '', 'Village Status': 'Inhabitant', 'Census 2001 Code': '01552300', 'Census 2011 Code': '022455'}
            if count % 100000 == 0:
                print(f'processed {count} villages')

            state_code = r['State Code']
            state_name = r['State Name (In English)']
            dist_code  = r['District Code']
            dist_name  = r['District Name (In English)']
            subdist_code = r['Sub-District Code']
            subdist_name = r['Sub-District Name (In English)']
            village_name = r['Village Name (In Englsih)']
            village_code = r['Village Code']

            info = {
                'census2001_code': r['Census 2001 Code'],
                'census2011_code': r['Census 2011 Code'],
                'version'        : r['Village Version'],
                'status'         : r['Village Status'],
                'name_l'         : r['Village Name (In Local)'],
            }

            if subdist_code not in hierarchies['subdistricts']:
                report_validation_error('subdistcode invalid in village file parsing',
                                        '{} for {} in village file is invalid'.format(subdist_code, village_name),
                                        (village_filename, r))
                continue
             
            state_code_known = hierarchies['subdistricts'][subdist_code][0]
            if state_code_known != state_code:
                report_validation_error('state code mismatch in village file parsing',
                                        '{} for {} in village file doesnt match existing {}'.format(state_code, village_name, state_code_known),
                                        (village_filename, r))
                continue

            state_name_known = all_info_by_code[state_code]['name']
            if state_name_known != state_name:
                report_validation_error('state name mismatch in village file parsing',
                                        '{} for {} in village file doesnt match existing {}'.format(state_name, village_name, state_name_known),
                                        (village_filename, r))
                continue


            dist_code_known = hierarchies['subdistricts'][subdist_code][1]
            if dist_code_known != dist_code:
                report_validation_error('dist code mismatch in village file parsing',
                                        '{} for {} in village file doesnt match existing {}'.format(dist_code, village_name, dist_code_known),
                                        (village_filename, r))
                continue
            dist_info_by_code = all_info_by_code[state_code]['districts'][dist_code]

            dist_name_known = dist_info_by_code['name']
            if dist_name_known != dist_name:
                report_validation_error('dist name mismatch in village file parsing',
                                        '{} for {} in village file doesnt match existing {}'.format(dist_name, village_name, dist_name_known),
                                        (village_filename, r))
                continue

            subdist_info_by_code = dist_info_by_code['subdistricts'][subdist_code]
            subdist_name_known = subdist_info_by_code['name']
            if subdist_name_known != subdist_name:
                report_validation_error('subdist name mismatch in village file parsing',
                                        '{} for {} in village file doesnt match existing {}'.format(subdist_name, village_name, subdist_name_known),
                                        (village_filename, r))
                continue

            subdist_info = all_info[state_name]['districts'][dist_name]['subdistricts'][subdist_name]
            if 'villages' not in subdist_info_by_code:
                subdist_info_by_code['villages'] = {}
            if 'villages' not in subdist_info:
                subdist_info['villages'] = {}

            # N.B.: village names can repeat within a sub district
            if village_name not in subdist_info['villages']:
                subdist_info['villages'][village_name] = []

            if len(subdist_info['villages'][village_name]) > 0:
                if village_code == subdist_info['villages'][village_name][0]['code']:
                    continue

            subdist_info['villages'][village_name].append(info)
            by_code_info = copy.copy(info)
            info['code'] = village_code
            by_code_info['name'] = village_name
            if village_code in subdist_info_by_code['villages']:
                prev = subdist_info_by_code['villages'][village_code]
                report_validation_error('village code repeated in village file parsing',
                                        '{} for {} is repeated in village file, prev: {}'.format(village_code, subdist_name, prev),
                                        (village_filename, r, prev))
                continue

            subdist_info_by_code['villages'][village_code] = by_code_info
            if village_code in hierarchies['villages']:
                prev = hierarchies['villages'][village_code]
                report_validation_error('village code global repeat in village file parsing',
                                        '{} for {}, {}, {} is repeated, prev: {}'.format(village_code, subdist_name, dist_name, state_name, prev),
                                        (village_filename, r, prev))
                continue
            hierarchies['villages'][village_code] = [state_code, dist_code, subdist_code]
            count += 1


def parse_villages_blocks_file(input_folder, all_info, all_info_by_code, hierarchies):
    village_blocks_filename = '{}/villages_by_blocks.csv'.format(input_folder)
    with open(village_blocks_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        localbody_info = {}
        for r in reader:
            #{'State code': '19', 'State Name(In English)': 'WEST BENGAL', 'State census code': '19', 'District code': '306', 'District Name(In English)': 'PURBA BARDHAMAN', 'District census code': '335', 'Subdistrict code': '2278', 'Subdistrict Name(In English)': 'Mangolkote', 'Subdistrict census code': '2278', 'Village code': '319067', 'Village Name(In English)': 'Taldanga', 'VillageCunsecCode': '319067', 'Localbody Code': '108657', 'Localbody Name(In English)': 'PALIGRAM', 'Localbody Census Code': '0', 'Block code': '2815', 'Block Name(In English)': 'MANGOLKOTE'}
            if count % 100000 == 0:
                print(f'processed {count} villages')

            state_code   = r['State code']
            dist_code    = r['District code']
            subdist_code = r['Subdistrict code']
            block_code   = r['Block code']
            village_code = r['Village code']
            localbody_code = r['Localbody Code']

            state_name   = r['State Name(In English)']
            dist_name    = r['District Name(In English)']
            subdist_name = r['Subdistrict Name(In English)']
            block_name   = r['Block Name(In English)']
            village_name = r['Village Name(In English)']
            localbody_name = r['Localbody Name(In English)']

            if village_code == '' and village_name == '':
                continue

            if village_code in hierarchies['villages_by_blocks']:
                if localbody_info[village_code] == localbody_code:
                    prev = hierarchies['villages_by_blocks'][village_code]
                    report_validation_error('village code global repeat in village block file parsing',
                                            '{} for {}, {}, {}, {} is repeated, prev: {}'.format(village_code, village_name, block_name, dist_name, state_name, prev),
                                            (village_blocks_filename, r, prev))
                continue

            localbody_info[village_code] = localbody_code
            hierarchies['villages_by_blocks'][village_code] = [state_code, dist_code, block_code]
           
            if village_code not in hierarchies['villages']:
                report_validation_error('invalid village code in village block file parsing',
                                        'village code {} missing for {}'.format(village_code, village_name),
                                        (village_blocks_filename, r))
                continue
            v = hierarchies['villages'][village_code]
            v_v = [state_code, dist_code, subdist_code]
            if v_v[0] != v[0] or v_v[1] != v[1] or v_v[2] != v[2]:
                report_validation_error('village hierarchy mismatch in village block file parsing',
                                        'village hierarchy {} expected for {} but got {}'.format(v, village_name, v_v),
                                        (village_blocks_filename, r))
                continue

            if block_code == '':
                dist_info_by_code  = all_info_by_code[state_code]['districts'][dist_code]
                if 'villages_not_covered_by_blocks' not in dist_info_by_code:
                    dist_info_by_code['villages_not_covered_by_blocks'] = {}

                dist_info = all_info[state_name]['districts'][dist_name]
                if 'villages_not_covered_by_blocks' not in dist_info:
                    dist_info['villages_not_covered_by_blocks'] = {}
                if village_name not in dist_info['villages_not_covered_by_blocks']:
                    dist_info['villages_not_covered_by_blocks'][village_name] = []

                dist_info['villages_not_covered_by_blocks'][village_name].append(village_code)
                dist_info_by_code['villages_not_covered_by_blocks'][village_code] = village_name
                continue

            if block_code not in hierarchies['blocks']:
                report_validation_error('invalid block code in village block file parsing',
                                        'block code {} missing for {}'.format(block_code, village_name),
                                        (village_blocks_filename, r))
                continue

            b_s = hierarchies['blocks'][block_code]
            b_b = [state_code, dist_code]
            b_m = None
            for b in b_s:
                if b[0] == b_b[0] and b[1] == b_b[1]:
                    b_m = b
                    break

            if b_m is None:
                report_validation_error('block hierarchy mismatch in village block file parsing',
                                        'block hierarchy {} expected for {}, {} but got {}'.format(b_s, block_name, village_name, b_b),
                                        (village_blocks_filename, r))
                continue


            block_info_by_code = all_info_by_code[state_code]['districts'][dist_code]['blocks'][block_code]
            if 'villages' not in block_info_by_code:
                block_info_by_code['villages'] = {}
            block_info_by_code['villages'][village_code] = village_name
            
            block_info = all_info[state_name]['districts'][dist_name]['blocks'][block_name]
            if 'villages' not in block_info:
                block_info['villages'] = {}
            if village_name not in block_info['villages']:
                block_info['villages'][village_name] = []
            block_info['villages'][village_name].append(village_code)
            count += 1

        all_village_ids = set(hierarchies['villages'].keys())
        all_village_ids_blockwise = set(hierarchies['villages_by_blocks'].keys())

        missing_in_blockwise = all_village_ids - all_village_ids_blockwise
        missing_in_main = all_village_ids_blockwise - all_village_ids
        if len(missing_in_main):
            report_validation_error('extra villages in village block file parsing',
                                    'extra villages {} in village block mapping'.format(missing_in_main),
                                    (village_blocks_filename, missing_in_main))
        if len(missing_in_blockwise):
            report_validation_error('missing villages in village block file parsing',
                                    'missing villages {} in village block mapping'.format(missing_in_blockwise),
                                    (village_blocks_filename, missing_in_blockwise))



def parse_gp_file(input_folder, all_info, all_info_by_code, hierarchies):
    gps_filename = '{}/gp_mapping.csv'.format(input_folder)
    with open(gps_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        for r in reader:
            #{'District\nCode': '191', 'District Name\n(in English)': 'BEGUSARAI', 'District\nCensus\nCode\n2011': '222', 'District\nCensus\nCode\n2001': '20', 'Sub District\nCode': '1315', 'Sub District Name\n(in English)': 'Naokothi', 'Sub District\nCensus\nCode\n2011': '01315', 'Sub District\nCensus\nCode\n2001': '12', 'Village\nCode': '238187', 'Village Name\n(in English)': 'Manerpur', 'Village\nCensus\nCode\n2011': '238187', 'Village\nCensus\nCode\n2001': '02230600', 'Local Body\nCode': '94446', 'Local Body Name\n(in English)': 'BISHNUPUR', 'State Code': '10', 'State Name': 'BIHAR'}
            if count % 100000 == 0:
                print(f'processed {count} villages')

            state_code   = r['State Code']
            dist_code    = r['District\nCode']
            subdist_code = r['Sub District\nCode']
            village_code = r['Village\nCode']
            localbody_code = r['Local Body\nCode']

            state_name   = r['State Name']
            dist_name    = r['District Name\n(in English)']
            subdist_name = r['Sub District Name\n(in English)']
            village_name = r['Village Name\n(in English)']
            localbody_name = r['Local Body Name\n(in English)']

            if village_code not in hierarchies['villages']:
                report_validation_error('invalid village code in gp file parsing',
                                        'village code {} missing for {}'.format(village_code, village_name),
                                        (gps_filename, r))
                continue

            v = hierarchies['villages'][village_code]
            v_v = [state_code, dist_code, subdist_code]
            if v_v[0] != v[0] or v_v[1] != v[1] or v_v[2] != v[2]:
                report_validation_error('village hierarchy mismatch in gp file parsing',
                                        'village hierarchy {} expected for {} but got {}'.format(v, village_name, v_v),
                                        (gps_filename, r))
                continue

            if localbody_code not in hierarchies['gps']:
                hierarchies['gps'][localbody_code] = []
            hierarchies['gps'][localbody_code].append([state_code, dist_code, subdist_code])

            subdist_info_by_code = all_info_by_code[state_code]['districts'][dist_code]['subdistricts'][subdist_code]
            if 'gps' not in subdist_info_by_code:
                subdist_info_by_code['gps'] = {}
            subdist_info = all_info[state_name]['districts'][dist_name]['subdistricts'][subdist_name]
            if 'gps' not in subdist_info:
                subdist_info['gps'] = {}

            if localbody_code not in subdist_info_by_code['gps']:
                subdist_info_by_code['gps'][localbody_code] = {
                        'name': localbody_name,
                        'villages': {}
                }
            gp_info_by_code = subdist_info_by_code['gps'][localbody_code]
            if localbody_name not in subdist_info['gps']:
                subdist_info['gps'][localbody_name] = {
                        'code': localbody_code,
                        'villages': {}
                }
            gp_info = subdist_info['gps'][localbody_name]
            if village_code not in gp_info_by_code['villages']:
                gp_info_by_code['villages'][village_code] = village_name

            if village_name not in gp_info['villages']:
                gp_info['villages'][village_name] = []
            gp_info['villages'][village_name].append(village_code)


            #    prev = gp_info['villages'][village_name]
            #    report_validation_error('village name repeat in gp file parsing',
            #                            'village name {}({}) repeated for {}, {}, {}, {}, prev: {}'.format(
            #                            village_name, village_code, localbody_name, subdist_name, dist_name, state_name, prev),
            #                            (gps_filename, r, prev))
            #    continue


            path = [state_code, dist_code, subdist_code, localbody_code]
            if village_code not in hierarchies['villages_by_gps']: 
                hierarchies['villages_by_gps'][village_code] = []
            hierarchies['villages_by_gps'][village_code].append(path)

            #    prev = hierarchies['villages_by_gps'][village_code]
            #    report_validation_error('village code global repeat in gp file parsing',
            #                            'village code {}({}) repeated globally for {}, prev: {}'.format(village_code, village_name, path, prev),
            #                            (gps_filename, r, prev))
            #    continue

            count += 1

        all_village_ids = set(hierarchies['villages'].keys())
        all_village_ids_gpwise = set(hierarchies['villages_by_gps'].keys())

        missing_in_gpwise = all_village_ids - all_village_ids_gpwise
        missing_in_main = all_village_ids_gpwise - all_village_ids
        if len(missing_in_main):
            report_validation_error('extra villages in village gp file parsing',
                                    'extra villages {} in village gp mapping'.format(missing_in_main),
                                    (village_blocks_filename, missing_in_main))
        if len(missing_in_gpwise):
            report_validation_error('missing villages in village gp file parsing',
                                    'missing villages {} in village gp mapping'.format(missing_in_gpwise),
                                    (village_blocks_filename, missing_in_gpwise))



def parse_local_body_file(filename, mode, all_info, all_info_by_code, hierarchies):
    with open(filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        for r in reader:

            if count % 50000 == 0:
                print(f'processed {count} local bodies')

            #print(r)
            #{'Local Body Code': '133607', 'Local Body Version': '1', 'Local Body Name (IN English)': 'KOLEGAON', 'Local Body Name (In Local)': 'कोलगांव', 'Local Body Type Code': '3', 'Local Body Type Name': 'Village Panchayat', 'Intermediate/Block Panchayat Code': '4130', 'District Panchayat Code': '353', 'State Code': '23', 'State Name (In Local)': 'MADHYA PRADESH'}

            localbody_name = r['Local Body Name (IN English)']
            localbody_code = r['Local Body Code']
            intermediate_p_code = r['Intermediate/Block Panchayat Code']
            dist_p_code = r['District Panchayat Code']
            state_code = r['State Code']

            info = {
                'version'  : r['Local Body Version'],
                'name_l'   : r['Local Body Name (In Local)'],
                'type_code': r['Local Body Type Code'],
                'type_name': r['Local Body Type Name'],
                'mode': mode,
            }
            # 1 - 'District Panchayat'
            # 2 - 'Intermediate/Block Panchayat'
            # 3 - 'Village Panchayat'

            if info['type_code'] == '3':
                if localbody_code not in hierarchies['gps']:
                    report_validation_error('invalid local body code in {} localbody file parsing'.format(mode),
                                            'invalid local body code {} in {} localbody file parsing: {}'.format(localbody_code, mode, r),
                                            (filename, r))
                    continue

                paths = hierarchies['gps'][localbody_code]
                for path in paths:
                    state_code_known = path[0]
                    dist_code_known = path[1]
                    subdist_code_known = path[2]
                    state_name_known = all_info_by_code[state_code_known]['name']
                    dist_name_known = all_info_by_code[state_code_known]['districts'][dist_code_known]['name']
                    subdist_name_known = all_info_by_code[state_code_known]['districts'][dist_code_known]['subdistricts'][subdist_code_known]['name']

                    all_info_by_code[state_code_known]['districts'][dist_code_known]['subdistricts'][subdist_code_known]['gps'][localbody_code].update(info)
                    all_info[state_name_known]['districts'][dist_name_known]['subdistricts'][subdist_name_known]['gps'][localbody_name].update(info)

            # TODO: capture intermediate, district panchayat hierarchies and their mapping to block, subdistrict and districts
            count += 1


            

def parse_ulbs_mapping_file(input_folder, all_info, all_info_by_code, hierarchies):
    ulbs_mapping_filename = '{}/statewise_ulbs_coverage.csv'.format(input_folder)
    with open(ulbs_mapping_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        for r in reader:
            #{'S.No': '22,076', 'State Name': 'WEST BENGAL', 'Localbody': '250034', 'Localbody Name': 'Durgapur', 'Census 2011 Code': '801674', 'District Code': '704', 'District Name': 'PASCHIM BARDHAMAN', 'Subdistrict Code': '', 'Subdistrict Name': '', 'Village Code': '', 'Village Name': ''}
            count += 1
            if count == 1:
                continue
            state_name = r['State Name']  
            dist_name = r['District Name']
            subdist_name = r['Subdistrict Name']
            localbody_name = r['Localbody Name']
            village_name = r['Village Name']

            state_code = all_info[state_name]['code']
            dist_code = r['District Code']
            subdist_code = r['Subdistrict Code']
            localbody_code = r['Localbody']
            village_code = r['Village Code']

            
            if localbody_code not in hierarchies['ulbs']:
                hierarchies['ulbs'][localbody_code] = []

            def is_in(existing, path):
                already_seen = False
                for e in existing:
                    if len(e) != len(path):
                        return already_seen
                    match = True
                    for i, p in enumerate(path):
                        if p != e[i]:
                            match = False
                            break
                    already_seen = match
                    if match:
                        break
                return already_seen


            existing = hierarchies['ulbs'][localbody_code]
            if subdist_code != '':
                path = [state_code, dist_code, subdist_code]
                to_add_by_code = all_info_by_code[state_code]['districts'][dist_code]['subdistricts'][subdist_code]
                to_add = all_info[state_name]['districts'][dist_name]['subdistricts'][subdist_name]
            elif dist_code != '':
                path = [state_code, dist_code]
                to_add_by_code = all_info_by_code[state_code]['districts'][dist_code]
                to_add = all_info[state_name]['districts'][dist_name]
            else:
                path = [state_code]
                to_add_by_code = all_info_by_code[state_code]
                to_add = all_info[state_name]

            if is_in(existing, path):
                existing.append(path)

            if 'ulbs' not in to_add:
                to_add['ulbs'] = {}
            if 'ulbs' not in to_add_by_code:
                to_add_by_code['ulbs'] = {}

            # TODO: check for name repeats
            if localbody_name not in to_add['ulbs']:
                to_add['ulbs'][localbody_name] = {
                    'census2011_code': r['Census 2011 Code'],
                    'code': localbody_code,
                    'villages': {}
                }
            if localbody_code not in to_add_by_code['ulbs']:
                to_add_by_code['ulbs'][localbody_code] = {
                    'census2011_code': r['Census 2011 Code'],
                    'name': localbody_name,
                    'villages': {}
                }

            if village_code != '':
                # TODO: check for name repeats
                to_add['ulbs'][localbody_name]['villages'][village_name] = village_code
                to_add_by_code['ulbs'][localbody_code]['villages'][village_code] = village_name
                path = [state_code, dist_code, subdist_code, localbody_code]
                if village_code in hierarchies['villages_by_ulbs']:
                    prev = hierarchies['villages_by_ulbs'][village_code]
                    report_validation_error('ulb village repeat in ulb mapping',
                                            'village {}({}) repeated for {}, {}, {}, {}, curr: {}, prev: {}'.format(
                                                village_code, village_name, localbody_name, subdist_name, dist_name, state_name, path, prev),
                                            (ulbs_mapping_filename, r))
                    continue
                hierarchies['villages_by_ulbs'][village_code] = path
            count += 1



def parse_ulbs_file(input_folder, all_info, all_info_by_code, hierarchies):
    ulbs_filename = '{}/urban_local_bodies.csv'.format(input_folder)
    with open(ulbs_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        for r in reader:
            #{'Local Body\nCode': '250179', 'Local Body\nVersion': '1', 'Local Body Name\n(In English)': 'Uttarpara Kotrung', 'Local Body Name\n(In Local)': '', 'Localbody\nType\nCode': '5', 'Census 2011 Code': '801732', 'State Code': '19', 'State Name(In English)': 'WEST BENGAL'}
            count += 1

            localbody_code = r['Local Body\nCode']
            state_name = r['State Name(In English)']
            if localbody_code not in hierarchies['ulbs']:
                report_validation_error('ulb missing in ulbs file',
                                        'ulb with code {} missing in ulbs file'.format(localbody_code),
                                        (ulbs_filename, r))
                continue

            info = {
                'version': r['Local Body\nVersion'],
                'name_l': r['Local Body Name\n(In Local)'],
                'type_code': r['Localbody\nType\nCode']
            }
            paths = hierarchies['ulbs'][localbody_code]
            for path in paths:
                if len(path) == 3:
                    to_add_by_code = all_info_by_code[path[0]]['districts'][path[1]]['subdistricts'][path[2]]['ulbs'][localbody_code]
                    state_name_known = all_info_by_code[path[0]]['name']
                    dist_name_known  = all_info_by_code[path[0]]['districts'][path[1]]['name']
                    subdist_name_known  = all_info_by_code[path[0]]['districts'][path[1]]['subdistricts'][path[2]]['name']
                    to_add = all_info_by_code[state_name_known]['districts'][dist_name_known]['subdistricts'][subdist_name_known]['ulbs'][localbody_name]
                elif len(path) == 2:
                    to_add_by_code = all_info_by_code[path[0]]['districts'][path[1]]['ulbs'][localbody_code]
                    state_name_known = all_info_by_code[path[0]]['name']
                    dist_name_known  = all_info_by_code[path[0]]['districts'][path[1]]['name']
                    to_add = all_info_by_code[state_name_known]['districts'][dist_name_known]['ulbs'][localbody_name]
                else:
                    to_add_by_code = all_info_by_code[path[0]]['ulbs'][localbody_code]
                    state_name_known = all_info_by_code[path[0]]['name']
                    to_add = all_info_by_code[state_name_known]['ulbs'][localbody_name]
 
                to_add.update(info)
                to_add_by_code(info)



def parse_constituency_mapping_file(input_folder, all_info, all_info_by_code, hierarchies):
    constituencies_filename = '{}/constituencies_mapping.csv'.format(input_folder)
    with open(constituencies_filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        for r in reader:
            #{'S.No.': '1235', 'Assembly Constituency Code': '2034', 'Assembly Constituency ECI Code': '220', 'Assembly Constituency Name': 'Nayagram', 'Parliament Constituency code': '243', 'Parliament Constituency ECI Code': '33', 'Parliament Constituency Name': 'Jhargram', 'State Name': 'WEST BENGAL', 'District Census 20^C11 Code': '000', 'District Code': '703', 'District Name': 'Jhargram', 'Subdistrict Census 2011 Code': '02456', 'Subdistrict Code': '2456', 'Subdistrict Name': 'Gopiballavpur - II', 'Block Code': '2985', 'Block Name': 'GOPIBALLAV PUR -II', 'Village Census 2011 Code': '340430', 'Village Code': '340430', 'Village Name': 'Ekdal', 'Localbody Code': '110356', 'Localbody Name': 'NOTA', 'State Code': '19'}
            #print(r)

            if count % 100000 == 0:
                print(f'processed {count} villages')

            village_code = r['Village Code']
            ac_code      = r['Assembly Constituency Code']
            pc_code      = r['Parliament Constituency code']
            lb_code      = r['Localbody Code']
            state_code   = r['State Code']
            dist_code    = r['District Code']
            subdist_code = r['Subdistrict Code']
            block_code   = r['Block Code']

            village_name = r['Village Name']
            ac_name      = r['Assembly Constituency Name']
            pc_name      = r['Parliament Constituency Name']

            if village_code not in hierarchies['villages']:
                report_validation_error('invalid village code in constituency file parsing',
                                        'village code {} missing for {}'.format(village_code, village_name),
                                        (constituencies_filename, r))
                continue

            v = hierarchies['villages'][village_code]
            v_v = [state_code, dist_code, subdist_code]
            if v_v[0] != v[0] or v_v[1] != v[1] or v_v[2] != v[2]:
                report_validation_error('village hierarchy mismatch in constituency file parsing',
                                        'village hierarchy {} expected for {} but got {}'.format(v, village_name, v_v),
                                        (constituencies_filename, r))
                continue

            count += 1




"""
invalidated_census_villages.csv nofn_panchayats.csv
"""


if __name__ == "__main__":
    #TODO: consider adding a sqlite file as well
    all_info = {}
    all_info_by_code = {}
    hierarchies = {
        'districts': {},
        'subdistricts': {},
        'blocks': {},
        'gps': {},
        'villages': {},
        'villages_by_blocks': {},
        'villages_by_gps': {},
        'villages_by_ulbs': {},
        'villages_by_acs': {},
        'villages_by_pcs': {},
        'ulbs': {},
        'pcs': {},
        'acs': {}
    }
    mark_phase('LATEST_FOLDER_SEARCH', 'searching for latest folder')
    input_folder = get_latest_folder()
    print(f'found folder {input_folder}')
    mark_phase('PARSE_STATES_FILE', 'parsing states file')
    parse_states_file(input_folder, all_info, all_info_by_code)
    mark_phase('PARSE_DISTS_FILE', 'parsing districts file')
    parse_dists_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_SUBDISTS_FILE', 'parsing subdistricts file')
    parse_subdists_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_BLOCKS_FILE', 'parsing blocks file')
    parse_blocks_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_VILLAGES_FILE', 'parsing villages file')
    parse_villages_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_VILLAGES_BLOCKS_FILE', 'parsing villages by blocks file')
    parse_villages_blocks_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_GP_MAPPING_FILE', 'parsing gp mapping file')
    parse_gp_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_LOCAL_BODY_FILES', 'parsing local body files')
    filename = '{}/traditional_local_bodies.csv'.format(input_folder)
    parse_local_body_file(filename, 'traditional', all_info, all_info_by_code, hierarchies)
    filename = '{}/pri_local_bodies.csv'.format(input_folder)
    parse_local_body_file(filename, 'pri', all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_ULBS_MAPPING_FILE', 'parsing urban local body mapping file')
    parse_ulbs_mapping_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_ULBS_FILE', 'parsing urban local body files')
    parse_ulbs_file(input_folder, all_info, all_info_by_code, hierarchies)
    mark_phase('PARSE_CONSTITUENCIES_FILE', 'parsing constituency mapping files')
    parse_constituency_mapping_file(input_folder, all_info, all_info_by_code, hierarchies)

    #pprint(all_info)
    for desc, errors in all_errors.items():
        pprint('{}: {}'.format(desc, len(errors)))
