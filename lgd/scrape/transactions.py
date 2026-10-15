"""The transaction report that replaced LGD's entity-level changes report."""

import csv
import shutil
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

from .base import (BaseDownloader, DownloaderItem, MultiDownloader,
                   INCORRECT_CAPTCHA_MESSAGE, get_date_str)


TRANSACTION_COLUMNS = ('Transaction ID', 'Operation Code', 'Operation Name',
                       'Description', 'Transaction Date')


class TransactionCaptchaError(ValueError):
    pass


def parse_transaction_report(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='lgd_transaction_report')
    if table is None:
        # The same CAPTCHA error text also occurs in the page's JavaScript,
        # including successful responses. Only inspect the visible error.
        if INCORRECT_CAPTCHA_MESSAGE in soup.get_text(' ', strip=True):
            raise TransactionCaptchaError('Transaction report CAPTCHA rejected')
        if 'No Record Found' in set(soup.stripped_strings):
            return []
        raise ValueError('Transaction report has neither a results table nor an explicit no-records message')

    headers = [cell.get_text(' ', strip=True) for cell in table.select('thead th')]
    if headers != ['S No', *TRANSACTION_COLUMNS]:
        raise ValueError(f'Unexpected transaction report columns: {headers}')
    rows = table.select('tbody tr')
    if not rows:
        raise ValueError('Transaction results table is empty without an explicit no-records message')
    records = []
    for row in rows:
        cells = [cell.get_text(' ', strip=True) for cell in row.find_all('td', recursive=False)]
        if len(cells) != len(headers):
            raise ValueError(f'Unexpected transaction row: {cells}')
        record = dict(zip(headers[1:], cells[1:]))
        if not record['Transaction ID'].isdigit() or not record['Operation Code'].isdigit():
            raise ValueError(f'Invalid transaction identifiers: {record}')
        datetime.strptime(record['Transaction Date'], '%d-%b-%Y')
        records.append(record)
    return records


def missing_date_ranges(start, end, covered):
    """Inclusive, non-overlapping ranges, split at month/coverage boundaries."""
    current = start
    while current <= end:
        if current.isoformat() in covered:
            current += timedelta(days=1)
            continue
        first = current
        while (current < end and (current + timedelta(days=1)).month == first.month
               and (current + timedelta(days=1)).isoformat() not in covered):
            current += timedelta(days=1)
        yield first, current
        current += timedelta(days=1)


class TransactionRangeDownloader(BaseDownloader):
    def __init__(self, **kwargs):
        self.state_code = kwargs['state_code']
        self.state_name = kwargs['state_name']
        self.start_date = date.fromisoformat(kwargs['start_date'])
        self.end_date = date.fromisoformat(kwargs['end_date'])
        super().__init__(**kwargs)

    def get_filename(self):
        # Keep completed backfill ranges reusable across daily runs as well as
        # retries. They are removed only after the aggregate has been saved.
        return str(Path(self.ctx.params.base_raw_dir) / 'transactions' / 'parts' / self.csv_filename)

    def get_records(self):
        url = f'{self.base_url}/lgdTransaction.do'
        token = self.ctx.csrf_token_reports
        referer = f'{url}?OWASP_CSRFTOKEN={token}'
        for attempt in range(self.ctx.params.captcha_retries + 1):
            captcha = self.captcha_helper.get_code(referer)
            response = self.ctx.session.post(url, data={
                'OWASP_CSRFTOKEN': token,
                'stateCode': self.state_code,
                'stateNameEnglish': self.state_name,
                'correctionRadio': 'on',
                'fromDate': self.start_date.strftime('%d-%m-%Y'),
                'toDate': self.end_date.strftime('%d-%m-%Y'),
                'chapchaAnswers': captcha,
            }, headers={'referer': referer}, **self.ctx.params.request_args())
            response.raise_for_status()
            try:
                records = parse_transaction_report(response.text)
            except TransactionCaptchaError:
                self.captcha_helper.mark_failure()
                if attempt == self.ctx.params.captcha_retries:
                    raise
                time.sleep(1)
                continue
            self.captcha_helper.mark_success()
            for record in records:
                day = datetime.strptime(record['Transaction Date'], '%d-%b-%Y').date()
                if not self.start_date <= day <= self.end_date:
                    raise ValueError(f'Transaction date {day} is outside the requested range')
                record['State Code'] = self.state_code
                record['State Name'] = self.state_name
            return records


class TransactionsDownloader(MultiDownloader):
    def __init__(self, **kwargs):
        kwargs['deps'] = ['STATES']
        super().__init__(**kwargs)
        self.history_dir = Path(self.ctx.params.base_raw_dir) / 'transactions'
        self.previous_file = self.history_dir / 'combined.csv'
        self.coverage_file = self.history_dir / 'dates_covered.txt'
        self.covered_dates = set()
        self.requested_dates = set()

    def date_range(self):
        start = date.fromisoformat(self.ctx.params.transactions_start_date)
        # Today's report is still changing. Only mark complete days as covered.
        end = datetime.strptime(get_date_str(), '%d%b%Y').date() - timedelta(days=1)
        return start, end

    def is_done(self):
        if not (super().is_done() and self.previous_file.exists() and self.coverage_file.exists()):
            return False
        start, end = self.date_range()
        covered = set(self.coverage_file.read_text().splitlines())
        return next(missing_date_ranges(start, end, covered), None) is None

    def download(self, ctx=None):
        if ctx is not None:
            self.set_context(ctx)
        if self.is_done():
            return
        # Rebuild an unfinished aggregate, or one whose requested backfill has
        # widened. Completed range files and combined.csv remain reusable.
        Path(self.get_filename()).unlink(missing_ok=True)
        super().download()

    def populate_downloaders(self):
        if self.downloader_items is not None:
            return
        if self.coverage_file.exists():
            if not self.previous_file.exists():
                raise ValueError('Transaction coverage exists without the corresponding historical CSV')
            self.covered_dates = set(self.coverage_file.read_text().splitlines())
        start, end = self.date_range()
        ranges = list(missing_date_ranges(start, end, self.covered_dates))
        states = [('0', 'Center')]
        states.extend((row['State Code'], row['State Name (In English)'])
                      for row in BaseDownloader.records_from_downloader('STATES'))
        self.downloader_items = []
        for first, last in ranges:
            self.requested_dates.update((first + timedelta(days=i)).isoformat()
                                        for i in range((last - first).days + 1))
            for state_code, state_name in states:
                name = f'{self.name}_{state_code}_{first.isoformat()}_{last.isoformat()}'
                downloader = TransactionRangeDownloader(
                    name=name, base_name=self.name, ctx=self.ctx,
                    csv_filename=f'{name.lower()}.csv',
                    state_code=state_code, state_name=state_name,
                    start_date=first.isoformat(), end_date=last.isoformat())
                self.downloader_items.append(DownloaderItem(downloader, {}))

    def combine_records(self):
        records = super().combine_records()
        if self.previous_file.exists():
            with self.previous_file.open() as source:
                records.extend(csv.DictReader(source))
        # Repeated publication/checkpoint recovery must not duplicate records.
        # Include all fields: do not collapse distinct descriptions under one ID.
        unique = {tuple(record[column] for column in (*TRANSACTION_COLUMNS, 'State Code', 'State Name')): record
                  for record in records}
        return sorted(unique.values(), key=lambda record: (
            datetime.strptime(record['Transaction Date'], '%d-%b-%Y'),
            int(record['State Code']), int(record['Transaction ID'])))

    def cleanup(self):
        self.history_dir.mkdir(parents=True, exist_ok=True)
        if Path(self.get_filename()).stat().st_size == 0:
            with open(self.get_filename(), 'w') as output:
                csv.writer(output).writerow((*TRANSACTION_COLUMNS, 'State Code', 'State Name'))
        # Save the data before advancing coverage. If interrupted between the
        # two replacements, the next run safely fetches/deduplicates it again.
        temporary = self.previous_file.with_suffix('.tmp')
        shutil.copyfile(self.get_filename(), temporary)
        temporary.replace(self.previous_file)
        temporary = self.coverage_file.with_suffix('.tmp')
        temporary.write_text(''.join(day + '\n' for day in sorted(self.covered_dates | self.requested_dates)))
        temporary.replace(self.coverage_file)
        super().cleanup()
