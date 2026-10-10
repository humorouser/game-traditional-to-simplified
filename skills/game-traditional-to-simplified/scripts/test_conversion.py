"""Synthetic edge-case tests, not evidence of a working game mod."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import opencc
from convert_localization import transform, validate, convert_file, load_json

G=load_json(Path(__file__).with_name('glossary.json'))
CC=opencc.OpenCC('tw2sp.json')
def doc(rows):
    return {'schema_version':1,'metadata':{'language':'TraditionalChinese','lossless':True,'source_role':'synthetic_test','resource':'SYNTHETIC_NOT_GAME','id_format':'hex32'},'entries':[{'id':f'{i:08X}','text':s} for i,s in enumerate(rows)]}

class Tests(unittest.TestCase):
    def test_requested_examples(self):
        for s,t in [('繼續遊戲','继续游戏'),('任務完成','任务完成'),('遊戲設定','游戏设置'),('記憶體','内存')]: self.assertEqual(transform(s,CC,G),t)
    def test_protected_and_non_chinese(self):
        s='任務 {任務名} ${玩家} {{變量}} %1$s %02d %PLAYER% <tag attr="繁體">完成</tag> [按鈕] $變量 ABC 123 😀\\n\\u4E00\r\n\t'
        d=doc([s]); e=copy.deepcopy(d);e['entries'][0]['text']=transform(s,CC,G)
        self.assertTrue(validate(d,e,G)['text_validation_passed'])
        self.assertIn('{任務名}',e['entries'][0]['text'])
    def test_quotes_and_real_newlines(self):
        s='他說："任務完成"，\n繼續遊戲\r\n路徑 C:\\Games\\test'
        self.assertEqual(transform(s,CC,G),'他说："任务完成"，\n继续游戏\r\n路径 C:\\Games\\test')
    def test_empty_preserved(self):
        d=doc(['']);self.assertTrue(validate(d,d,G)['text_validation_passed'])
    def test_corruption_detected(self):
        d=doc(['任務 {0}']);e=copy.deepcopy(d);e['entries'][0]['text']='任务 {1}';self.assertFalse(validate(d,e,G)['text_validation_passed'])
    def test_mapping_order_detected(self):
        d=doc(['甲','乙']);e=copy.deepcopy(d);e['entries'].reverse();self.assertFalse(validate(d,e,G)['text_validation_passed'])
    def test_histogram_failure_detected(self):
        d=doc(['任務']);e=copy.deepcopy(d);e['entries'][0]['text']='任务';r=validate(d,e,G,{'codepoints':[ord('任')]});self.assertEqual(len(r['missing_histogram_characters']),1)
    def test_names_can_be_protected(self):
        g={'protected_terms':['測試地名'],'replacements':{}};self.assertEqual(transform('前往測試地名完成任務',CC,g),'前往測試地名完成任务')
    def test_actual_character_name(self):
        self.assertEqual(transform('塑膠怪: 任務完成。',CC,{'replacements':{'塑膠怪':'塑胶怪'}}),'塑胶怪: 任务完成。')
    def test_reject_ascii_glossary(self):
        with self.assertRaises(ValueError):transform('任務',CC,{'replacements':{'任務':'Task'}})
    def test_lossless_roundtrip_and_repeat(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'input.json';p.write_text(json.dumps(doc(['任務 {0}\r\n"記憶體"',''])),encoding='utf-8')
            a=convert_file(p,Path(t)/'results',Path(__file__).with_name('glossary.json'))
            b=convert_file(p,Path(t)/'results',Path(__file__).with_name('glossary.json'))
            self.assertEqual(a,b);self.assertEqual(p.read_bytes(),(Path(t)/'results/original_backup.json').read_bytes())
    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d=doc(['甲','乙']);d['entries'][1]['id']=d['entries'][0]['id'];p=Path(t)/'a.json';p.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(ValueError):convert_file(p,Path(t)/'out',Path(__file__).with_name('glossary.json'))
    def test_identical_duplicate_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            d=doc(['任務','任務']);d['entries'][1]['id']=d['entries'][0]['id'];p=Path(t)/'a.json';p.write_text(json.dumps(d),encoding='utf-8')
            r=convert_file(p,Path(t)/'out',Path(__file__).with_name('glossary.json'))
            self.assertEqual(r['count_converted'],2);self.assertEqual(r['duplicate_id_rows'],1)
    def test_lossy_input_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d=doc(['甲']);d['metadata']['lossless']=False;p=Path(t)/'a.json';p.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(ValueError):convert_file(p,Path(t)/'out',Path(__file__).with_name('glossary.json'))

    def test_visible_brackets_not_protected_by_default(self):
        self.assertEqual(transform('[任務完成]',CC,G),'[任务完成]')
    def test_engine_bracket_token_can_be_protected(self):
        g={'additional_protected_regex':[r'\[[^\]]+\]']}
        self.assertEqual(transform('[按鈕] 任務完成',CC,g),'[按鈕] 任务完成')
    def test_arbitrary_string_and_integer_ids(self):
        with tempfile.TemporaryDirectory() as t:
            d=doc(['任務','記憶體']);d['metadata'].pop('id_format');d['entries'][0]['id']='UI_START';d['entries'][1]['id']=37
            p=Path(t)/'input.json';p.write_text(json.dumps(d),encoding='utf-8')
            convert_file(p,Path(t)/'result',Path(__file__).with_name('glossary.json'))
            self.assertEqual([r['id'] for r in load_json(Path(t)/'result/simplified.json')['entries']],['UI_START',37])
    def test_game_output_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'source.json';p.write_text(json.dumps(doc(['任務'])),encoding='utf-8')
            with self.assertRaises(ValueError):convert_file(p,Path(t)/'game/out',Path(__file__).with_name('glossary.json'),game_roots=[Path(t)/'game'])
    def test_float_and_bool_ids_refused(self):
        for sid in (1.5,True):
            with tempfile.TemporaryDirectory() as t:
                d=doc(['任務']);d['metadata'].pop('id_format');d['entries'][0]['id']=sid
                p=Path(t)/'source.json';p.write_text(json.dumps(d),encoding='utf-8')
                with self.assertRaises(ValueError):convert_file(p,Path(t)/'result',Path(__file__).with_name('glossary.json'))
    def test_same_hex_id_case_conflict_refused(self):
        with tempfile.TemporaryDirectory() as t:
            d=doc(['甲','乙']);d['entries'][0]['id']='aabbccdd';d['entries'][1]['id']='AABBCCDD'
            p=Path(t)/'source.json';p.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(ValueError):convert_file(p,Path(t)/'result',Path(__file__).with_name('glossary.json'))

if __name__=='__main__': unittest.main(verbosity=2)
