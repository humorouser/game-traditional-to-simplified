"""Small synthetic font tests: no game resources or downloaded binaries required."""
import json
from pathlib import Path
import tempfile
import unittest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from font_tools import audit, unify


def make_font(path, donor=False, han_width=1024):
    cmap = {32:'space',65:'A',49:'one',0xE000:'icon',ord('任'):'ren'}
    if donor: cmap[ord('务')] = 'wu'
    order = ['.notdef'] + list(cmap.values())
    fb = FontBuilder(1024, isTTF=True); fb.setupGlyphOrder(order); fb.setupCharacterMap(cmap)
    glyf = {}; widths = {}
    for n in order:
        pen = TTGlyphPen(None)
        if n != 'space':
            x = 70 if donor else 30
            pen.moveTo((x,0)); pen.lineTo((x+150,0)); pen.lineTo((x+150,700)); pen.lineTo((x,700)); pen.closePath()
        glyf[n] = pen.glyph(); widths[n] = (han_width if n in ('ren','wu') else 512,0)
    fb.setupGlyf(glyf); fb.setupHorizontalMetrics(widths); fb.setupHorizontalHeader(ascent=900,descent=-124)
    fb.setupNameTable({'familyName':'Synthetic test','styleName':'Regular','uniqueFontIdentifier':'Synthetic test','fullName':'Synthetic test','psName':'Synthetic-test'})
    fb.setupOS2(sTypoAscender=900,sTypoDescender=-124,usWinAscent=900,usWinDescent=124)
    fb.setupPost(keepGlyphNames=False); fb.setupMaxp(); fb.save(path)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.original=self.root/'original.ttf';self.donor=self.root/'donor.ttf';self.text=self.root/'text.json'
        make_font(self.original);make_font(self.donor,donor=True)
        self.text.write_text(json.dumps({'entries':[{'id':'UI_START','text':'任务 A1 \ue000'}]},ensure_ascii=False),encoding='utf-8')
    def run_unify(self):
        return unify(self.original,self.donor,self.text,self.root/'result.ttf',self.root/'report.json')
    def test_real_missing_glyph_detected(self):
        r=audit(self.original,self.text);self.assertEqual(r['missing_count'],1);self.assertEqual(r['affected_rows'],1)
    def test_unified_glyphs_and_original_symbols_survive(self):
        r=self.run_unify();self.assertTrue(r['offline_passed']);self.assertEqual(r['uniform_han_count'],2)
        self.assertEqual(r['missing_after'],0);self.assertIsNone(r['applied_variable_weight'])
        old=TTFont(self.original);new=TTFont(self.root/'result.ttf')
        for cp in (65,49,0xE000):self.assertEqual(old.getGlyphID(old.getBestCmap()[cp]),new.getGlyphID(new.getBestCmap()[cp]))
    def test_missing_donor_fails(self):
        make_font(self.donor)
        with self.assertRaises(ValueError):self.run_unify()
    def test_source_overwrite_refused(self):
        with self.assertRaises(ValueError):unify(self.original,self.donor,self.text,self.original,self.root/'report.json')
    def test_game_output_refused(self):
        with self.assertRaises(ValueError):unify(self.original,self.donor,self.text,self.root/'game/font.ttf',self.root/'report.json',game_roots=[self.root/'game'])
    def test_han_width_mismatch_not_reported_as_success(self):
        make_font(self.donor,donor=True,han_width=900)
        with self.assertRaises(ValueError):self.run_unify()
        r=json.loads((self.root/'report.json').read_text());self.assertFalse(r['offline_passed'])


if __name__ == '__main__': unittest.main(verbosity=2)
