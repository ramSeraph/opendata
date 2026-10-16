import contextlib
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import archive_prev_month as archive


class FakeReleases:
    """In-memory release storage; archive creation and verification use real 7-Zip."""

    def __init__(self):
        self.assets = {}
        self.events = []
        self.overrides = {}
        self.fail_upload = None
        self.fail_delete = None

    def add(self, name, data, release='lgd-archive', state='uploaded'):
        self.assets[release, name] = (data, state)

    def metadata(self, release, name):
        value = self.assets.get((release, name))
        if value is None:
            return None
        data, state = value
        result = {'name': name, 'state': state, 'size': len(data),
                  'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                  'apiUrl': f'https://api.github.com/assets/{release}/{name}'}
        result.update(self.overrides.get(name, {}))
        return result

    def names(self, releases):
        return {name: release for release, name in self.assets if release in releases}

    def external(self, command):
        args = shlex.split(command)
        if args[:3] == ['gh', 'release', 'download']:
            name = args[args.index('-p') + 1]
            self.events.append(('download', name))
            Path(args[args.index('-O') + 1]).write_bytes(self.assets[args[3], name][0])
        elif args[:3] == ['gh', 'release', 'upload']:
            path = Path(args[4])
            self.events.append(('upload', path.name))
            if '--clobber' in args:
                self.assets.pop((args[3], path.name), None)
            if self.fail_upload == path.name:
                self.add(path.name, b'', args[3], state='starter')
                raise RuntimeError('upload interrupted')
            if (args[3], path.name) in self.assets:
                raise RuntimeError('asset already exists')
            self.add(path.name, path.read_bytes(), args[3])
        elif args[:3] == ['gh', 'release', 'delete-asset']:
            if self.fail_delete == args[4]:
                raise RuntimeError('delete interrupted')
            self.events.append(('delete', args[4]))
            del self.assets[args[3], args[4]]
        elif args[:4] == ['gh', 'api', '--method', 'DELETE']:
            key = next(key for key in self.assets if self.metadata(*key)['apiUrl'] == args[4])
            self.events.append(('discard_empty', key[1]))
            del self.assets[key]
        elif command.startswith('cd '):
            subprocess.run(command.replace('-md=1G', '-md=1m'), shell=True,
                           check=True, capture_output=True, text=True)
        else:
            raise AssertionError(f'Unexpected external command: {command}')

    @contextlib.contextmanager
    def installed(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(archive, 'get_all_releases', return_value=['lgd-latest', 'lgd-archive']))
            stack.enter_context(patch.object(archive, 'get_all_archive_names', side_effect=self.names))
            stack.enter_context(patch.object(archive, 'get_release_asset', side_effect=self.metadata))
            stack.enter_context(patch.object(archive, 'run_external', side_effect=self.external))
            yield


@unittest.skipUnless(shutil.which('7z'), '7z is required to exercise real archive headers')
class ArchiveTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='lgd archive test ')
        self.addCleanup(temp.cleanup)
        previous = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, previous)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.staging = Path('data/zipping_area')
        self.staging.mkdir(parents=True)
        self.final = Path('data/combined/states.Jan2026.7z')
        self.final.parent.mkdir(parents=True)
        self.files = [self.staging / f'states.{day:02d}Jan2026.csv' for day in (1, 2)]
        for index, file in enumerate(self.files):
            file.write_text(f'Code,Name\n{index},Example\n')
        self.remote = FakeReleases()
        self.initial_mapping = {'states': ['31Dec2025'], 'districts': ['30Dec2025']}
        self.remote.add('archive_mapping.json', json.dumps(self.initial_mapping).encode())
        for file in self.files:
            self.add_daily(file)

    def add_daily(self, file):
        packed = Path(file.name + '.7z')
        self.make_archive(packed, [file])
        self.remote.add(packed.name, packed.read_bytes(), release='lgd-latest')
        packed.unlink()

    def make_archive(self, path, files):
        subprocess.run(['7z', 'a', '-t7z', '-mx=1', str(path.resolve()),
                        *[file.name for file in files]], cwd=self.staging,
                       check=True, capture_output=True)

    def external(self, command):
        # Exercise the real compression command, using a small test dictionary.
        subprocess.run(command.replace('-md=1G', '-md=1m'), shell=True,
                       check=True, capture_output=True, text=True)

    def worker(self):
        with self.remote.installed(), patch.object(archive, 'refresh_indexes'), \
                patch.object(archive, 'redistribute_latest'):
            archive.archive_month('Jan2026')

    def assert_originals_retained(self):
        for file in self.files:
            self.assertIn(('lgd-latest', file.name + '.7z'), self.remote.assets)
        self.assertFalse(any(event[0] == 'delete' for event in self.remote.events))

    def corrupt_archive(self, path, files):
        subprocess.run(['7z', 'a', '-t7z', '-m0=Copy', '-mhc=off', str(path.resolve()),
                        *[file.name for file in files]], cwd=self.staging,
                       check=True, capture_output=True)
        payload = bytearray(path.read_bytes())
        payload[32] ^= 1
        path.write_bytes(payload)
        # The old filename-only validator accepted this corrupt payload.
        archive.validate_archive_files(path, [file.name for file in files])

    def test_atomic_compression_replaces_stale_temporary_and_lists_all_files(self):
        temporary = self.final.with_suffix('.7z.tmp')
        temporary.write_bytes(b'left over from an interrupted run')
        with patch.object(archive, 'run_external', side_effect=self.external):
            archive.compress_archive(self.final, self.files, self.staging)
        archive.validate_archive_files(self.final, [file.name for file in self.files])
        self.assertFalse(temporary.exists())

    def test_interrupted_or_failed_compression_never_publishes_temporary_file(self):
        for error in (RuntimeError('compression failed'), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                self.final.write_bytes(b'previous complete archive')
                temporary = self.final.with_suffix('.7z.tmp')

                def interrupt(command):
                    temporary.write_bytes(b'incomplete new archive')
                    raise error

                with patch.object(archive, 'run_external', side_effect=interrupt):
                    with self.assertRaises(type(error)):
                        archive.compress_archive(self.final, self.files, self.staging)
                self.assertEqual(self.final.read_bytes(), b'previous complete archive')
                self.assertFalse(temporary.exists())

    def test_header_validation_rejects_missing_members_and_accepts_completed_deletions(self):
        self.make_archive(self.final, self.files[:1])
        with self.assertRaises(ValueError):
            archive.validate_archive_files(self.final, [file.name for file in self.files])
        self.final.unlink()
        self.make_archive(self.final, self.files)
        archive.validate_archive_files(self.final, [self.files[1].name], allow_extra=True)
        with self.assertRaises(ValueError):
            archive.validate_archive_files(self.final, [self.files[1].name])

    def test_incomplete_member_list_is_not_published_as_a_completed_archive(self):
        temporary = self.final.with_suffix('.7z.tmp')
        with patch.object(archive, 'run_external', side_effect=lambda cmd: self.make_archive(temporary, self.files[:1])):
            with self.assertRaises(ValueError):
                archive.compress_archive(self.final, self.files, self.staging)
        self.assertFalse(self.final.exists())
        self.assertFalse(temporary.exists())

    def test_published_download_must_include_daily_sources_before_becoming_cached(self):
        wrong = Path('wrong.7z')
        self.make_archive(wrong, self.files[:1])
        temporary = self.final.with_suffix('.7z.tmp')
        self.remote.add(self.final.name, wrong.read_bytes())
        with self.remote.installed():
            with self.assertRaises(ValueError):
                archive.download_published_archive(self.final, 'lgd-archive', [f.name for f in self.files])
        self.assertFalse(self.final.exists())
        self.assertFalse(temporary.exists())

    def run_month(self, daily, published=(), fail_index=False, **options):
        events = []
        for file in self.staging.glob('*.csv'):
            if file.name + '.7z' in daily and ('lgd-latest', file.name + '.7z') not in self.remote.assets:
                self.add_daily(file)
        for key in list(self.remote.assets):
            if key[0] == 'lgd-latest' and key[1] not in daily:
                del self.remote.assets[key]
        for name in daily:
            if ('lgd-latest', name) not in self.remote.assets:
                self.remote.add(name, b'unrelated dataset', release='lgd-latest')
        for name in published:
            self.remote.add(name, self.final.read_bytes())

        def external(command):
            self.remote.external(command)
            args = shlex.split(command)
            if args[:3] == ['gh', 'release', 'upload']:
                events.append(('upload', Path(args[4]).name.split('.')[0]))
            elif args[:3] == ['gh', 'release', 'delete-asset']:
                events.append(('delete', args[4]))

        def indexes():
            events.append(('indexes',))
            if fail_index:
                raise RuntimeError('index upload failed')

        with contextlib.ExitStack() as stack:
            stack.enter_context(self.remote.installed())
            stack.enter_context(patch.object(archive, 'update_mapping', side_effect=lambda prefix, dates: events.append(('mapping', prefix))))
            stack.enter_context(patch.object(archive, 'refresh_indexes', side_effect=indexes))
            stack.enter_context(patch.object(archive, 'redistribute_latest', side_effect=lambda releases: events.append(('redistribute',))))
            stack.enter_context(patch.object(archive, 'run_external', side_effect=external))
            if fail_index:
                with self.assertRaisesRegex(RuntimeError, 'index upload failed'):
                    archive.archive_month('Jan2026', **options)
            else:
                archive.archive_month('Jan2026', **options)
        return events

    def test_invalid_cache_is_rebuilt_and_indexes_update_between_archives(self):
        self.final.write_bytes(b'interrupted legacy archive')
        district = self.staging / 'districts.01Jan2026.csv'
        district.write_text('Code,Name\n1,Example\n')
        events = self.run_month([f.name + '.7z' for f in self.files + [district]])
        self.assertEqual(events, [
            ('upload', 'states'), ('mapping', 'states'),
            ('delete', 'states.01Jan2026.csv.7z'), ('delete', 'states.02Jan2026.csv.7z'), ('indexes',),
            ('upload', 'districts'), ('mapping', 'districts'),
            ('delete', 'districts.01Jan2026.csv.7z'), ('indexes',), ('redistribute',), ('indexes',)])
        self.assertFalse(self.final.exists())

    def test_retry_finishes_publication_after_some_daily_sources_were_deleted(self):
        self.make_archive(self.final, self.files)
        events = self.run_month([self.files[1].name + '.7z'], [self.final.name])
        self.assertEqual(events, [('mapping', 'states'), ('delete', 'states.02Jan2026.csv.7z'),
                                  ('indexes',), ('redistribute',), ('indexes',)])

    def test_complete_cache_can_be_uploaded_without_downloading_daily_sources_again(self):
        self.make_archive(self.final, self.files)
        for file in self.files:
            file.unlink()
        events = self.run_month([file.name + '.7z' for file in self.files])
        self.assertEqual(events[0], ('upload', 'states'))
        self.assertFalse(self.final.exists())

    def test_index_failure_preserves_completed_cache_for_retry(self):
        events = self.run_month([f.name + '.7z' for f in self.files], fail_index=True)
        self.assertEqual(events[-1], ('indexes',))
        archive.validate_archive_files(self.final, [f.name for f in self.files])

    def test_indexes_are_refreshed_when_only_redistribution_remains(self):
        self.assertEqual(self.run_month([]), [('redistribute',), ('indexes',)])

    def test_monthly_archive_only_handles_selected_month(self):
        daily = [file.name + '.7z' for file in self.files]
        daily += ['districts.01Feb2026.csv.7z', 'states.01Feb2026.csv.7z']
        events = self.run_month(daily)
        self.assertEqual(events, [('upload', 'states'), ('mapping', 'states'),
                                 ('delete', 'states.01Jan2026.csv.7z'),
                                 ('delete', 'states.02Jan2026.csv.7z'), ('indexes',),
                                 ('redistribute',), ('indexes',)])

    def test_extraction_only_replaces_destination_after_success_including_empty_csv(self):
        file = self.files[0]
        packed = Path('daily.7z')
        temporary = file.with_suffix('.csv.tmp')
        for contents in (b'Code,Name\n1,Complete\n', b''):
            with self.subTest(contents=contents):
                file.write_bytes(contents)
                self.make_archive(packed, [file])
                file.write_bytes(b'previous destination')
                temporary.write_bytes(b'interrupted extraction')
                archive.extract_daily_archive(packed, file)
                self.assertEqual(file.read_bytes(), contents)
                self.assertFalse(temporary.exists())
                packed.unlink()

    def test_failed_or_interrupted_extraction_preserves_destination(self):
        file = self.files[0]
        packed = Path('daily.7z')
        self.make_archive(packed, [file])
        original = file.read_bytes()
        run = subprocess.run
        for error in (subprocess.CalledProcessError(2, '7z'), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                def interrupt(args, **kwargs):
                    if args[:3] == ['7z', 'e', '-so']:
                        kwargs['stdout'].write(b'partial data')
                        raise error
                    return run(args, **kwargs)
                with patch.object(archive.subprocess, 'run', side_effect=interrupt):
                    with self.assertRaises(type(error)):
                        archive.extract_daily_archive(packed, file)
                self.assertEqual(file.read_bytes(), original)
                self.assertFalse(file.with_suffix('.csv.tmp').exists())

    def test_failed_upload_preserves_sources_and_retry_replaces_empty_placeholder(self):
        self.remote.fail_upload = self.final.name
        with self.assertRaisesRegex(RuntimeError, 'upload interrupted'):
            self.worker()
        self.assert_originals_retained()
        self.assertTrue(self.final.exists())
        self.assertEqual(self.remote.assets['lgd-archive', self.final.name], (b'', 'starter'))
        self.remote.fail_upload = None
        self.worker()
        self.assertIn(('discard_empty', self.final.name), self.remote.events)
        self.assertGreater(len(self.remote.assets['lgd-archive', self.final.name][0]), 0)
        self.assertFalse(any(release == 'lgd-latest' for release, name in self.remote.assets))

    def test_cache_does_not_authorize_deletion_of_unverified_remote_asset(self):
        self.make_archive(self.final, self.files)
        self.remote.add(self.final.name, self.final.read_bytes())
        for metadata in ({'state': 'starter'}, {'state': 'uploaded', 'size': 0},
                         {'size': 1}, {'digest': 'sha256:' + '0' * 64}):
            with self.subTest(metadata=metadata):
                self.remote.overrides[self.final.name] = metadata
                with self.assertRaises(ValueError):
                    self.worker()
                self.assert_originals_retained()
                self.assertFalse(any(event[0] == 'upload' for event in self.remote.events))

    def test_new_upload_must_match_remote_digest_before_mapping_or_deletion(self):
        self.remote.overrides[self.final.name] = {'digest': 'sha256:' + '0' * 64}
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.worker()
        self.assert_originals_retained()
        self.assertTrue(self.final.exists())
        self.assertNotIn(('upload', 'archive_mapping.json'), self.remote.events)

    def test_corrupt_published_archive_does_not_authorize_deletion(self):
        self.corrupt_archive(self.final, self.files)
        self.remote.add(self.final.name, self.final.read_bytes())
        self.final.unlink()
        with self.assertRaises(subprocess.CalledProcessError):
            self.worker()
        self.assert_originals_retained()
        self.assertFalse(self.final.exists())
        self.assertFalse(self.final.with_suffix('.7z.tmp').exists())

    def test_corrupt_cache_is_rebuilt_from_daily_sources(self):
        self.corrupt_archive(self.final, self.files)
        self.worker()
        self.assertIn(('download', self.files[0].name + '.7z'), self.remote.events)
        self.final.write_bytes(self.remote.assets['lgd-archive', self.final.name][0])
        archive.test_archive_integrity(self.final)

    def test_old_staging_files_are_refreshed_before_compression(self):
        original = self.files[0].read_bytes()
        self.files[0].write_bytes(b'partial extraction from an older run')
        self.worker()
        self.final.write_bytes(self.remote.assets['lgd-archive', self.final.name][0])
        result = subprocess.run(['7z', 'e', '-so', str(self.final), self.files[0].name],
                                check=True, capture_output=True)
        self.assertEqual(result.stdout, original)

    def test_legacy_published_archive_without_digest_is_downloaded_and_tested_once(self):
        self.make_archive(self.final, self.files)
        self.remote.add(self.final.name, self.final.read_bytes())
        self.remote.overrides[self.final.name] = {'digest': None}
        self.final.unlink()
        self.worker()
        self.assertEqual(self.remote.events.count(('download', self.final.name)), 1)
        self.assertFalse(any(release == 'lgd-latest' for release, name in self.remote.assets))

    def test_digestless_remote_must_match_cache_bytes(self):
        self.make_archive(self.final, self.files)
        good = self.final.read_bytes()
        self.remote.add(self.final.name, b'x' * len(good))
        self.remote.overrides[self.final.name] = {'digest': None}
        with self.assertRaisesRegex(ValueError, 'differs from the published file'):
            self.worker()
        self.assert_originals_retained()
        self.assertFalse(self.final.with_suffix('.7z.verify.tmp').exists())
        self.remote.add(self.final.name, good)
        self.worker()
        self.assertFalse(any(release == 'lgd-latest' for release, name in self.remote.assets))

    def test_mapping_backup_failure_preserves_canonical_mapping_and_daily_sources(self):
        original = self.remote.assets['lgd-archive', 'archive_mapping.json']
        self.remote.fail_upload = 'archive_mapping.backup.json'
        with self.assertRaisesRegex(RuntimeError, 'upload interrupted'):
            self.worker()
        self.assert_originals_retained()
        self.assertEqual(self.remote.assets['lgd-archive', 'archive_mapping.json'], original)
        self.assertNotIn(('upload', 'archive_mapping.json'), self.remote.events)

    def test_interrupted_mapping_replacement_recovers_from_remote_backup(self):
        self.remote.fail_upload = 'archive_mapping.json'
        with self.assertRaisesRegex(RuntimeError, 'upload interrupted'):
            self.worker()
        self.assert_originals_retained()
        backup = self.remote.assets['lgd-archive', 'archive_mapping.backup.json']
        self.assertEqual(json.loads(backup[0]), self.initial_mapping)
        # A fresh runner can recover even when the canonical asset disappeared.
        del self.remote.assets['lgd-archive', 'archive_mapping.json']
        self.final.unlink()
        self.remote.fail_upload = None
        self.worker()
        mapping = json.loads(self.remote.assets['lgd-archive', 'archive_mapping.json'][0])
        self.assertEqual(set(mapping['states']), {'31Dec2025', '01Jan2026', '02Jan2026'})
        self.assertEqual(mapping['districts'], self.initial_mapping['districts'])
        self.assertIn(('download', 'archive_mapping.backup.json'), self.remote.events)

    def test_partial_deletion_retries_against_remote_archive_on_fresh_runner(self):
        self.remote.fail_delete = self.files[1].name + '.7z'
        with self.assertRaisesRegex(RuntimeError, 'delete interrupted'):
            self.worker()
        self.assertNotIn(('lgd-latest', self.files[0].name + '.7z'), self.remote.assets)
        self.assertIn(('lgd-latest', self.files[1].name + '.7z'), self.remote.assets)
        self.final.unlink()
        self.remote.fail_delete = None
        self.worker()
        self.assertEqual(self.remote.events.count(('upload', self.final.name)), 1)
        self.assertIn(('download', self.final.name), self.remote.events)
        self.assertFalse(any(release == 'lgd-latest' for release, name in self.remote.assets))


if __name__ == '__main__':
    unittest.main()
