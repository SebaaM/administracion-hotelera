from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from .fixtures import source_candidate
class CSVTests(SimpleTestCase):
    def test_roundtrip_preserves_notes_colors_and_formula_text(self):
        from imports.csv_io import read_csv,write_csv
        for text in ("=1+1","+texto","-texto","@texto","'=original","María, prueba\nsegunda línea"):
            row=source_candidate(source_id="f03c4ea3-eaf9-4fab-9ac5-14feffecf776",guest=text,status="CONFIRMED")
            result=read_csv(write_csv([row]))[0]
            for field in ("guest","notes","colors","start","end","source_id"):
                self.assertEqual(result[field],row[field])
    def test_duplicate_ids_and_grid_csv_rejected(self):
        from imports.csv_io import read_csv,write_csv
        row=source_candidate(source_id="f03c4ea3-eaf9-4fab-9ac5-14feffecf776")
        with self.assertRaises(ValidationError):read_csv(write_csv([row,row]))
        with self.assertRaises(ValidationError):read_csv(b"room,1,2,3\n2-a,Person,Person,Person")
