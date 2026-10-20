"""Download a resumable Wikidata dataset."""

import argparse

from raw_wikidata import download_query


DATASETS = {
    'states': 'Q131541',
    'divisions': 'Q1230708',
    'districts': 'Q1149652',
    'subdivisions': 'Q7631016',
    'subdistricts': 'Q105626471',
    'district_panchayats': 'Q2758248',
    'blocks': 'Q2775236',
    'block_panchayats': 'Q4927168',
}


def download_dataset(name):
    qid = DATASETS[name]
    query = f"SELECT DISTINCT ?item WHERE {{ ?item wdt:P31/wdt:P279* wd:{qid}. }}"
    return download_query(query, f'data/{name}.jsonl')


def main(argv=None):
    # Preserve the singular arguments used by existing download commands.
    names = {name: name for name in DATASETS}
    names.update({name.removesuffix('s'): name for name in DATASETS})
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', choices=names)
    args = parser.parse_args(argv)
    download_dataset(names[args.dataset])


if __name__ == '__main__':
    main()
