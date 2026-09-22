import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('sync', Path(__file__).resolve().parents[1] / 'scripts' / 'sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

class SyncTests(unittest.TestCase):
    def test_excel_dates(self):
        self.assertEqual(sync.parse_date('2008-02-29'), (2008,2,29))
        self.assertEqual(sync.parse_date('2月29日'), (None,2,29))
        self.assertEqual(sync.parse_date('1', True), (1904,1,2))
        with self.assertRaises(ValueError): sync.parse_date('2100-02-29')

    def test_validation_preserves_last_good_data(self):
        headers={'A':'姓名','B':'职能组','C':'出生日期'}
        rows=[(1,headers),(2,{'A':'A','B':'组','C':'2000-01-01'}),(3,{'A':'B','B':'组','C':'wrong'})]
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'birthdays.json'; target.write_text('{"version":"old"}')
            with patch.object(sync,'read_rows',return_value=(rows,False)), patch.object(sync,'DATA',target):
                with self.assertRaisesRegex(ValueError,'第 3 行'): sync.sync(Path('dummy'))
            self.assertEqual(json.loads(target.read_text())['version'],'old')

    def test_exact_duplicates_only_and_no_birth_year_exported(self):
        rows=[(1,{'A':'姓名','B':'职能组','C':'出生日期','D':'分工'}),
              (2,{'A':'A','B':'组','C':'2000-01-01','D':'成员'}),
              (3,{'A':'A','B':'组','C':'2000-01-01','D':'成员'}),
              (4,{'A':'A','B':'组','C':'2000-01-01','D':'委员'})]
        with patch.object(sync,'read_rows',return_value=(rows,False)):
            payload,version,warnings=sync.convert(Path('dummy'))
        self.assertEqual(len(payload['members']),2)
        self.assertEqual(set(payload['members'][0]), {'name','group','month','day'})
        self.assertIn('1 条', warnings[0])

if __name__ == '__main__': unittest.main()
