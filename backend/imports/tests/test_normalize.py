from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from .fixtures import calendar
from imports.readers import read_xlsx,suggest_configuration
class NormalizeTests(SimpleTestCase):
    def test_nights_use_exclusive_checkout(self):
        from imports.normalize import normalize_calendar
        source=read_xlsx(calendar());cfg=suggest_configuration(source)
        rows=normalize_calendar(source,cfg,{"#C6EFCE":"Pagado"})
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]["start"],rows[0]["end"]),("2026-08-10","2026-08-13"))
        self.assertEqual(rows[0]["notes"][0]["text"],"Llegada tarde\nPedido especial")
        self.assertEqual(rows[0]["colors"][0]["meaning"],"Pagado")
    def test_color_change_does_not_split_stay(self):
        from imports.normalize import normalize_calendar
        source=read_xlsx(calendar())
        for c in source["sheets"][0]["cells"]:
            if c["ref"]=="L2":c["color"]="#FFE598"
        rows=normalize_calendar(source,suggest_configuration(source),{})
        self.assertEqual(len(rows),1)
        self.assertEqual(len(rows[0]["colors"]),3)
    def test_name_on_red_checkout_requires_review(self):
        from imports.normalize import normalize_calendar
        source=read_xlsx(calendar())
        for c in source["sheets"][0]["cells"]:
            if c["ref"]=="N2":c["value"]="Persona ficticia"
        rows=normalize_calendar(source,suggest_configuration(source),{})
        self.assertEqual(rows[0]["end"],"2026-08-13")
        self.assertTrue(any("salida" in warning for warning in rows[0]["warnings"]))
    def test_invalid_day_configuration_rejected(self):
        from imports.normalize import normalize_calendar
        source=read_xlsx(calendar());cfg=suggest_configuration(source);cfg[0]["month"]=0
        with self.assertRaises(ValidationError):normalize_calendar(source,cfg,{})
