import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import archive_prev_month as archive


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

    def make_archive(self, path, files):
        subprocess.run(['7z', 'a', '-t7z', '-mx=1', str(path.resolve()),
                        *[file.name for file in files]], cwd=self.staging,
                       check=True, capture_output=True)

    def external(self, command):
        # Exercise the real compression command, using a small test dictionary.
        subprocess.run(command.replace('-md=1G', '-md=1m'), shell=True,
                       check=True, capture_output=True, text=True)

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
        with patch.object(archive, 'run_external', side_effect=lambda cmd: shutil.copyfile(wrong, temporary)):
            with self.assertRaises(ValueError):
                archive.download_published_archive(self.final, 'lgd-archive', [f.name for f in self.files])
        self.assertFalse(self.final.exists())
        self.assertFalse(temporary.exists())

    def run_month(self, daily, published=(), fail_index=False, **options):
        events = []

        def upload(filename, counts, releases):
            prefix = Path(filename).name.split('.')[0]
            expected = [name.removesuffix('.7z') for name in daily
                        if name.startswith(prefix + '.') and name.endswith('Jan2026.csv.7z')]
            archive.validate_archive_files(Path(filename), expected)
            events.append(('upload', prefix))

        def external(command):
            if command.startswith('gh release delete-asset '):
                events.append(('delete', command.split()[4]))
            elif command.startswith('cd '):
                self.external(command)
            else:
                self.fail(f'Unexpected external command: {command}')

        def indexes():
            events.append(('indexes',))
            if fail_index:
                raise RuntimeError('index upload failed')

        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(archive, 'get_all_releases', return_value=['lgd-latest', 'lgd-archive']))
            stack.enter_context(patch.object(archive, 'get_all_archive_names', side_effect=[
                dict.fromkeys(daily, 'lgd-latest'), dict.fromkeys(published, 'lgd-archive')]))
            stack.enter_context(patch.object(archive, 'upload_to_archive', side_effect=upload))
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

    def test_catchup_worker_only_handles_selected_month_and_component(self):
        daily = [file.name + '.7z' for file in self.files]
        daily += ['districts.01Jan2026.csv.7z', 'states.01Feb2026.csv.7z']
        events = self.run_month(daily, component='states', redistribute=False)
        self.assertEqual(events, [('upload', 'states'), ('mapping', 'states'),
                                 ('delete', 'states.01Jan2026.csv.7z'),
                                 ('delete', 'states.02Jan2026.csv.7z'), ('indexes',), ('indexes',)])


if __name__ == '__main__':
    unittest.main()
