import json
import argparse
import csv

def process_geojson(input_file, output_file, gtiff_list_file):
    with open(input_file, 'r') as f:
        data = json.load(f)

    valid_ids = set()
    with open(gtiff_list_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name']:
                valid_ids.add(row['name'].replace('.tif', ''))

    filtered_features = []
    for feature in data['features']:
        if 'EVEREST_SH' in feature['properties']:
            everest_sh = feature['properties']['EVEREST_SH']
            feature_id = everest_sh.replace('/', '_')
            if feature_id in valid_ids:
                feature['properties']['id'] = feature_id
                filtered_features.append(feature)

    data['features'] = filtered_features

    with open(output_file, 'w') as f:
        json.dump(data, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Enhance a GeoJSON file with an 'id' property and filter based on a list of GTiffs.")
    parser.add_argument('input_file', help="The input GeoJSON file.")
    parser.add_argument('output_file', help="The output GeoJSON file.")
    parser.add_argument('gtiff_list', help="The CSV file containing the list of GTiffs.")
    args = parser.parse_args()

    process_geojson(args.input_file, args.output_file, args.gtiff_list)
