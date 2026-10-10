"""Headless, read-only Catalyst export -> OpenCC -> font -> validated fbmod.

Codex invokes this entrypoint. No Editor/Manager GUI, game writes or launch.
Only the verified 1.0.6.3 archive and known Catalyst game head are accepted.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile

SCRIPTS = Path(__file__).resolve().parent
ASSETS = SCRIPTS.parent / 'assets/catalyst'
EDITOR_HASH = '6eca779aac4a150f1c46934c0455522269a1820b6d3e0b8727c13a81ca9106f8'
FONT_HASH = 'a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da'
FONT_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf'
OFL_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/OFL.txt'
EDITOR_URL = 'https://github.com/CadeEvs/FrostyToolsuite/releases/download/v1.0.6.3/FrostyEditor.zip'


def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def outside_game(p, game):
    p, game = Path(p).resolve(), Path(game).resolve()
    if p == game or game in p.parents:
        raise ValueError('Working path resolves inside game: '+str(p))
    return p


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def source_snapshot(game):
    records = {}
    for name in ('Data','Patch','Core'):
        start = game/name
        if not start.exists():
            continue
        for directory, folders, files in os.walk(start, followlinks=False):
            # Never follow externally redirected resource directories.
            folders[:] = [n for n in folders if (Path(directory)/n).resolve().is_relative_to(game)]
            for name in files:
                file = Path(directory)/name
                if not file.resolve().is_relative_to(game):
                    raise ValueError('Original resource redirects outside game: '+str(file))
                stat = file.stat()
                records[str(file.relative_to(game))] = [stat.st_size,stat.st_mtime_ns]
    return records


def run(args, log, cwd=None):
    # Argument arrays avoid shell interpolation; stdout stays in the work directory.
    with Path(log).open('w', encoding='utf-8') as f:
        result = subprocess.run([str(x) for x in args], cwd=cwd, stdout=f,
                                stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise RuntimeError('Stage failed; inspect '+str(log))


def fetch(url, target, expected=None):
    target = Path(target)
    if target.exists():
        if expected and digest(target) != expected:
            raise ValueError('Cached dependency checksum differs: '+str(target))
        return
    temporary = target.with_suffix(target.suffix+'.download')
    request = urllib.request.Request(url, headers={'User-Agent': 'Codex-local-localization'})
    with urllib.request.urlopen(request, timeout=90) as response, temporary.open('wb') as f:
        shutil.copyfileobj(response, f)
    if expected and digest(temporary) != expected:
        raise ValueError('Downloaded dependency changed; do not execute it: '+str(temporary))
    temporary.replace(target)


def extract_verified(archive, output):
    if digest(archive) != EDITOR_HASH:
        raise ValueError('Requires verified official Frosty Editor 1.0.6.3 archive')
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            p = (output/entry.filename).resolve()
            if output.resolve() not in p.parents and p != output.resolve():
                raise ValueError('Unsafe dependency archive path')
        z.extractall(output)
    candidates = list(output.rglob('FrostySdk.dll'))
    if len(candidates) != 1:
        raise ValueError('Unexpected official SDK layout')
    return candidates[0].parent


def encode(source, target, output):
    sys.path.insert(0, str(ASSETS/'vendor/flammenwerfer'))
    from flammenwerfer.localization import Histogram, StringsBinary
    rows = json.loads((source/'all_rows.json').read_text(encoding='utf-8'))['entries']
    wanted = json.loads(Path(target).read_text(encoding='utf-8'))['entries']
    h = Histogram(str(source/'histogram.chunk'))
    b = StringsBinary(h, str(source/'binary.chunk'))
    if [pair[0] for pair in b.hashPairList] != [int(r['id'], 16) for r in rows]:
        raise ValueError('Independent source ID table differs')
    if any(b.stringList[int(r['id'], 16)] != r['text'] for r in rows):
        raise ValueError('Source text differs between official SDK and independent reader')
    # Check raw duplicate records independently, since official reader is ID keyed.
    pairs = {}
    raw = (source/'binary.chunk').read_bytes()
    for pair in b.hashPairList:
        begin = b.stringsOffset + pair[1] + 8
        encoded_text = raw[begin:raw.index(b'\x00',begin)]
        if pair[0] in pairs and encoded_text != pairs[pair[0]]:
            raise ValueError('Duplicate ID with conflicting encoded text requires investigation')
        pairs[pair[0]] = encoded_text
    added = h.add_chars_from_strings([''.join(c for c in r['text'] if ord(c)>=128) for r in rows+wanted])
    b.import_strings({int(r['id'],16):r['text'] for r in wanted})
    output.mkdir()
    h.save(str(output/'expanded_histogram.chunk'))
    b.update(h); b.save(str(output/'simplified_binary.chunk'))
    decoded = StringsBinary(Histogram(str(output/'expanded_histogram.chunk')),
                            str(output/'simplified_binary.chunk'))
    order = [pair[0] for pair in decoded.hashPairList] == [int(r['id'],16) for r in wanted]
    texts = all(decoded.stringList[int(r['id'],16)] == r['text'] for r in wanted)
    report = {'rows':len(rows), 'added_characters':added, 'id_order_duplicate_rows_exact':order,
              'texts_exact':texts, 'roundtrip_valid':order and texts, 'game_written':False}
    save(output/'report.json', report)
    if not report['roundtrip_valid']:
        raise ValueError('Encoding roundtrip failed')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game-root', required=True)
    p.add_argument('--work-root', required=True)
    p.add_argument('--frosty-archive', help='Reuse the verified official archive, never an arbitrary DLL directory')
    p.add_argument('--donor-font', help='Reuse the verified Noto Sans SC variable font')
    p.add_argument('--donor-license', help='Local OFL license to accompany reused font')
    p.add_argument('--glossary', help='Optional game glossary; defaults preserve official Catalyst names')
    a = p.parse_args()
    game = Path(a.game_root).resolve()
    work = outside_game(a.work_root, game)
    if not (game/'MirrorsEdgeCatalyst.exe').is_file() or not (game/'Data').is_dir() or not (game/'Patch').is_dir():
        raise ValueError('Not the verified Catalyst game layout')
    work.mkdir(parents=True, exist_ok=True)
    # Missing Python packages are provisioned in the task's isolated runtime.
    if any(importlib.util.find_spec(m) is None for m in ('opencc','fontTools','PIL')):
        runtime = work/'runtime'; python = runtime/'Scripts/python.exe'
        if Path(sys.executable).resolve() == python.resolve():
            raise RuntimeError('Runtime dependencies remain unavailable after provisioning')
        if not python.exists():
            run([sys.executable,'-m','venv',runtime], work/'runtime-create.log')
        run([python,'-m','pip','install','--index-url','https://pypi.org/simple',
             '-r',SCRIPTS/'requirements.txt'], work/'runtime-install.log')
        return subprocess.call([str(python),str(Path(__file__).resolve()),*sys.argv[1:]])
    run_dir = work/('run_'+uuid.uuid4().hex)
    run_dir.mkdir()
    print('Work directory: '+str(run_dir), flush=True)
    report = {'status':'running','game_root':str(game),'game_written':False,
              'installed':False,'game_launched':False,'in_game_verified':False}
    try:
        before = source_snapshot(game)
        save(run_dir/'original_resource_stat_before.json',before)
        deps = run_dir/'dependencies'; deps.mkdir()
        if a.frosty_archive:
            archive = Path(a.frosty_archive).resolve()
        else:
            archive = work/'FrostyEditor-1.0.6.3.zip'; fetch(EDITOR_URL, archive, EDITOR_HASH)
        sdk = extract_verified(archive, deps/'sdk')
        font = deps/'NotoSansSC-wght.ttf'
        if a.donor_font:
            if digest(a.donor_font)!=FONT_HASH:
                raise ValueError('Unverified donor font; inspect first')
            shutil.copy2(a.donor_font,font)
        else:
            fetch(FONT_URL,font,FONT_HASH)
        license_path = deps/'NotoSansSC-OFL.txt'
        if a.donor_license:
            shutil.copy2(a.donor_license,license_path)
        else:
            fetch(OFL_URL,license_path)
        compiler = Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        if not compiler.is_file():
            raise ValueError('Requires Windows x64 .NET Framework C# compiler')
        backend = sdk/'CatalystBackend.exe'
        run([compiler,'/nologo','/target:exe','/platform:x64','/out:'+str(backend),
             '/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',
             '/reference:'+str(sdk/'FrostySdk.dll'),'/reference:'+str(sdk/'FrostyCore.dll'),
             '/reference:'+str(sdk/'Plugins/FsLocalizationPlugin.dll'),ASSETS/'CatalystBackend.cs'],run_dir/'compile.log')
        source = run_dir/'original'
        run([backend,sdk,game,source],run_dir/'export.log',cwd=sdk)
        # Tests precede full conversion; logs are concise and do not dump the corpus.
        run([sys.executable,SCRIPTS/'test_conversion.py'],run_dir/'conversion-tests.log')
        run([sys.executable,SCRIPTS/'test_font_tools.py'],run_dir/'font-tests.log')
        run([sys.executable,SCRIPTS/'test_automation.py'],run_dir/'automation-tests.log')
        from convert_localization import convert_file
        from font_tools import audit, unify
        converted = run_dir/'converted'
        glossary = Path(a.glossary).resolve() if a.glossary else ASSETS/'glossary.json'
        text_report = convert_file(source/'all_rows.json',converted,glossary,game_roots=[game])
        shutil.copy2(glossary,converted/'glossary.json')
        target = converted/'simplified.json'
        encoded = run_dir/'encoded'; encoding_report = encode(source,target,encoded)
        fixed = run_dir/'uniform_font.ttf'
        save(run_dir/'font_before.json',audit(source/'original_font.ttf',target))
        print('Text and encoding passed; unifying all Chinese glyphs...',flush=True)
        font_report = unify(source/'original_font.ttf',font,target,fixed,run_dir/'font_report.json',400,[game])
        mod = run_dir/'mod'
        run([backend,sdk,game,run_dir/'source_crosscheck',target,encoded,mod,fixed],run_dir/'build.log',cwd=sdk)
        build = json.loads((mod/'mod_build_report.json').read_text(encoding='utf-8'))
        if not all(build[k] for k in ('mod_structure_valid','ebx_chunk_size_links_valid','compressed_payloads_verified','font_resource_payload_verified')):
            raise ValueError('Packaged resource validation failed')
        after = source_snapshot(game)
        save(run_dir/'original_resource_stat_after.json',after)
        if before != after:
            raise ValueError('Original resource sizes/timestamps changed during the run; investigate before installation')
        shutil.copy2(license_path,mod/license_path.name)
        (mod/'README.md').write_text('此包由 skill 后台构建；使用游戏官方繁体中文槽位。\n'
            '文字、编码、字体与 MOD 读回已验证；本次新包尚未进行游戏内验证。\n'
            '安装需遵守当前用户授权，不能把已生成等同于已启用。\n'
            '如使用 Frosty：导入、应用并勾选本包，停用旧中文/字体包，再从管理器启动。\n'
            '停用本包后恢复官方繁体；不覆盖原版资源。\n',encoding='utf-8')
        report.update(status='offline_passed',rows=text_report['count_original'],changed=text_report['changed'],
                      added_encoding_characters=encoding_report['added_characters'],missing_font_characters=font_report['missing_after'],
                      uniform_han_count=font_report['uniform_han_count'],fbmod=build['fbmod'],fbproject=build['fbproject'],
                      mod_sha256=digest(build['fbmod']),frosty_archive_sha256=digest(archive),donor_sha256=digest(font),
                      backend_source_sha256=digest(ASSETS/'CatalystBackend.cs'),
                      source_export_sha256=digest(source/'all_rows.json'),
                      original_resource_stat_unchanged=True,
                      original_resource_verification_scope='Data/Patch/Core file sizes and mtime; not full byte hashes')
        save(run_dir/'automation_report.json',report)
        save(work/'latest_run.json',{'run_directory':str(run_dir),'report':str(run_dir/'automation_report.json')})
        print(json.dumps(report,ensure_ascii=True),flush=True)
        return 0
    except Exception as error:
        report.update(status='failed',error=str(error))
        save(run_dir/'automation_report.json',report)
        print('Stopped: '+str(error),file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
