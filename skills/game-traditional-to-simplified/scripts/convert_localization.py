"""Local, repeatable OpenCC conversion of lossless game localization JSON. Never edits game files."""
import argparse
import copy
import csv
import hashlib
import importlib.metadata
import json
import re
from pathlib import Path

import opencc

HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003134f]+')
TOKEN = re.compile(
    r'<[^<>]*>|\[\[[^\]]*\]\]|'
    r'\$\{[^}]*\}|\{\{[^}]*\}\}|\{[^{}]*\}|'
    r'\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|.)|'
    r'%(?:%|(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hlLzjt])?[diuoxXfFeEgGaAcspn]|[A-Za-z_][\w]*%)|'
    r'\$[\w]+|https?://[^\s<>]+|[\x00-\x1f\x7f-\x9f]'
)
def identity(value, metadata):
    if metadata.get('id_format') == 'hex32':
        return ('hex32', int(value, 16))
    return (type(value).__name__, value)


def sha(data):
    return hashlib.sha256(data).hexdigest()

def load_json(path):
    # Strict decoding; replacement characters are never silently introduced.
    return json.loads(Path(path).read_text(encoding='utf-8-sig', errors='strict'))

def save_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', errors='strict')

def spans(text, glossary):
    protected = glossary.get('protected_terms', [])
    patterns = [TOKEN.pattern] + glossary.get('additional_protected_regex', [])
    if protected:
        patterns.insert(0, '|'.join(re.escape(x) for x in sorted(protected, key=len, reverse=True)))
    return re.compile('|'.join('(?:'+p+')' for p in patterns))

def transform(text, converter, glossary):
    terms = glossary.get('replacements', {})
    for k, v in terms.items():
        if not isinstance(k, str) or not isinstance(v, str) or not HAN.fullmatch(k) or not HAN.fullmatch(v):
            raise ValueError('Glossary replacements must contain Chinese characters only: '+repr(k))
    term_re = re.compile('|'.join(re.escape(k) for k in sorted(terms, key=len, reverse=True))) if terms else None
    def han_replace(m):
        value = m.group()
        if term_re is None:
            return converter.convert(value)
        # Substitute exact original terms; convert other text independently.
        result, pos = [], 0
        for term in term_re.finditer(value):
            result += [converter.convert(value[pos:term.start()]), terms[term.group()]]
            pos = term.end()
        result.append(converter.convert(value[pos:]))
        return ''.join(result)
    result, pos = [], 0
    for token in spans(text, glossary).finditer(text):
        result += [HAN.sub(han_replace, text[pos:token.start()]), token.group()]
        pos = token.end()
    result.append(HAN.sub(han_replace, text[pos:]))
    return ''.join(result)

def validate(source, converted, glossary, histogram=None):
    errors, warnings = [], []
    a, b = source['entries'], converted['entries']
    if len(a) != len(b): errors.append({'kind': 'count_mismatch'})
    if [(type(x['id']),x['id']) for x in a] != [(type(x['id']),x['id']) for x in b]: errors.append({'kind': 'id_or_order_mismatch'})
    if source['metadata'] != converted['metadata']: errors.append({'kind': 'metadata_mismatch'})
    t2s = opencc.OpenCC('t2s.json')
    missing, residual = {}, []
    allowed = set(histogram['codepoints']) if histogram else None
    for old, new in zip(a, b):
        sid, s, t = old['id'], old['text'], new['text']
        if {k:v for k,v in old.items() if k!='text'} != {k:v for k,v in new.items() if k!='text'}:
            errors.append({'id':sid,'kind':'row_metadata_mismatch'})
        if [m.group() for m in spans(s,glossary).finditer(s)] != [m.group() for m in spans(t,glossary).finditer(t)]:
            errors.append({'id':sid,'kind':'protected_token_mismatch'})
        if HAN.sub('',s) != HAN.sub('',t): errors.append({'id':sid,'kind':'non_chinese_changed'})
        if s and not t: errors.append({'id':sid,'kind':'unexpected_empty'})
        if not s: warnings.append({'id':sid,'kind':'original_empty_preserved'})
        if '\ufffd' in s or '\ufffd' in t: errors.append({'id':sid,'kind':'replacement_character'})
        try: t.encode('utf-8',errors='strict')
        except UnicodeError: errors.append({'id':sid,'kind':'invalid_unicode'})
        if '\x00' in t: warnings.append({'id':sid,'kind':'NUL_requires_engine_storage_verification'})
        if transform(t,t2s,glossary) != t: residual.append(sid)
        if allowed is not None:
            for char in set(t):
                if ord(char)>=128 and ord(char) not in allowed:
                    entry=missing.setdefault(char, {'char':char,'codepoint':f'U+{ord(char):04X}','occurrences_in_entries':0,'sample_ids':[]})
                    entry['occurrences_in_entries'] += 1
                    if len(entry['sample_ids'])<5: entry['sample_ids'].append(sid)
    return {'count_original':len(a),'count_converted':len(b),'unique_id_count':len(set(identity(x['id'],source['metadata']) for x in a)),
            'duplicate_id_rows':len(a)-len(set(identity(x['id'],source['metadata']) for x in a)),
            'changed':sum(x['text']!=y['text'] for x,y in zip(a,b)),
            'errors':errors,'warnings':warnings,'text_validation_passed':not errors,
            'traditional_residual_count':len(residual),'traditional_residual_sample_ids':residual[:20],
            'histogram_checked':allowed is not None,'missing_histogram_characters':list(missing.values()),
            'resource_import_validated':False,'font_glyphs_validated':False,'game_launched':False,
            'mod_build_ready':False}

def convert_file(input_path, output_dir, glossary_path, histogram_path=None, game_roots=()):
    input_path, output_dir = Path(input_path).resolve(), Path(output_dir).resolve()
    for game_root in game_roots:
        game = Path(game_root).resolve()
        if output_dir == game or game in output_dir.parents: raise ValueError('Refusing output inside game directory')
    if input_path == output_dir or output_dir in input_path.parents: raise ValueError('Use an output directory separate from source')
    source = load_json(input_path)
    if source.get('schema_version') != 1 or source.get('metadata',{}).get('lossless') is not True:
        raise ValueError('Requires schema_version=1, metadata.lossless=true; verify the exporter first')
    if source['metadata'].get('language') not in ('TraditionalChinese','zh-TW','zh-Hant'): raise ValueError('Expected TraditionalChinese source')
    entries = source.get('entries')
    if not isinstance(entries,list) or not entries: raise ValueError('No source entries')
    ids=[]
    for row in entries:
        if not isinstance(row,dict) or not isinstance(row.get('text'),str):
            raise ValueError('Each entry requires a text string')
        sid=row.get('id')
        if type(sid) not in (str,int) or (isinstance(sid,str) and not sid):
            raise ValueError('Each ID must be a nonempty string or an integer, never float/bool')
        if source['metadata'].get('id_format')=='hex32' and (not isinstance(sid,str) or not re.fullmatch(r'[0-9A-Fa-f]{8}',sid)):
            raise ValueError('hex32 IDs require exactly eight hex digits')
        ids.append(identity(sid,source['metadata']))
    values={}
    for key,row in zip(ids,entries):
        if key in values and values[key] != row['text']:
            raise ValueError('Duplicate ID has conflicting texts: '+repr(row['id']))
        values[key]=row['text']
    glossary=load_json(glossary_path)
    histogram=load_json(histogram_path) if histogram_path else None
    if histogram and histogram.get('resource') != source['metadata'].get('resource'):
        raise ValueError('Histogram resource does not match source resource')
    result=copy.deepcopy(source)
    tw=opencc.OpenCC('tw2sp.json'); ts=opencc.OpenCC('t2s.json')
    comparisons=[]
    for index,(old,new) in enumerate(zip(entries,result['entries'])):
        new['text']=transform(old['text'],tw,glossary)
        base=transform(old['text'],ts,{'protected_terms':glossary.get('protected_terms',[]), 'additional_protected_regex':glossary.get('additional_protected_regex',[])})
        comparisons.append([index,old['id'],old['text'],new['text'],base,base!=new['text']])
    report=validate(source,result,glossary,histogram)
    report.update({'source_role':source['metadata'].get('source_role'), 'source_sha256':sha(input_path.read_bytes()),
                   'glossary_sha256':sha(Path(glossary_path).read_bytes()),'opencc_version':importlib.metadata.version('opencc'),
                   'config':'tw2sp.json','term_and_name_review':'Pending human review of full game corpus'})
    output_dir.mkdir(parents=True,exist_ok=True)
    backup=output_dir/'original_backup.json'
    if backup.exists() and backup.read_bytes()!=input_path.read_bytes(): raise ValueError('Existing original backup differs; choose another output directory')
    backup.write_bytes(input_path.read_bytes())
    save_json(output_dir/'simplified.json',result)
    save_json(output_dir/'validation_report.json',report)
    with (output_dir/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['order','id','original_traditional','simplified_tw2sp_with_glossary','t2s_without_replacements','differs_from_t2s']);w.writerows(comparisons)
    if report['errors']: raise ValueError('Validation failed; see validation_report.json')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input'); p.add_argument('--output',required=True); p.add_argument('--glossary',default=str(Path(__file__).with_name('glossary.json')));p.add_argument('--histogram'); p.add_argument('--game-root', action='append',default=[])
    a=p.parse_args()
    r=convert_file(a.input,a.output,a.glossary,a.histogram,a.game_root)
    print(json.dumps({k:r[k] for k in ['count_original','count_converted','changed','text_validation_passed','histogram_checked','mod_build_ready']},ensure_ascii=True))
