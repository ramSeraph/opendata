"""Generate real Actions jobs/needs from the scraper's existing component DAG."""

import argparse
from pathlib import Path

from .daily_workflow import downloaders


LGD = Path(__file__).resolve().parents[1]
TEMPLATE = LGD / 'utils/templates/lgd_run.yml'
WORKFLOW = LGD.parent / '.github/workflows/lgd_run.yml'


def generate(items=None):
    items = downloaders() if items is None else items
    jobs = []
    for name, downloader in items.items():
        needs = ', '.join(['Prepare', *sorted(downloader.deps)])
        jobs.append(f'''  {name}:
    needs: [{needs}]
    permissions:
      contents: write
      actions: read
      checks: write
    uses: ./.github/workflows/lgd_component.yml
    with:
      component: {name}
      collection-date: ${{{{ needs.Prepare.outputs.date }}}}
      capacity-check: ${{{{ needs.Prepare.outputs.capacity }}}}
      assignment: ${{{{ toJSON(fromJSON(needs.Prepare.outputs.plan).{name}) }}}}
      prerequisites: ${{{{ toJSON(needs) }}}}
''')
    return TEMPLATE.read_text().replace('@@COMPONENT_JOBS@@', '\n'.join(jobs)).replace(
        '@@ALL_JOBS@@', ', '.join(['Prepare', *items]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = generate()
    if args.check:
        if not WORKFLOW.exists() or WORKFLOW.read_text() != expected:
            parser.exit(1, 'Daily workflow is stale. Run: cd lgd && uv run python -m utils.generate_daily_workflow\n')
        print('Daily workflow matches the component DAG.')
    else:
        WORKFLOW.write_text(expected)
        print(f'Generated {WORKFLOW}')


if __name__ == '__main__':
    main()
