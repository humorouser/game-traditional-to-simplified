"""Audit and unify standard TrueType Han glyphs on work copies, not game containers."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def is_han(cp):
    return (0x3400 <= cp <= 0x4DBF or 0x4E00 <= cp <= 0x9FFF
            or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x323AF)


def load_rows(path):
    doc = json.loads(Path(path).read_text(encoding='utf-8-sig', errors='strict'))
    rows = doc.get('entries')
    if not isinstance(rows, list) or not rows or any(
            not isinstance(r, dict) or not isinstance(r.get('text'), str) for r in rows):
        raise ValueError('Requires a nonempty entries list with text strings')
    return rows


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_outputs(outputs, sources, game_roots=()):
    outputs = [Path(p).resolve() for p in outputs]
    sources = [Path(p).resolve() for p in sources]
    if len(set(outputs)) != len(outputs):
        raise ValueError('Font output and report must have different paths')
    for out in outputs:
        if out in sources:
            raise ValueError('Never overwrite source font, donor or text')
        for game_root in game_roots:
            game = Path(game_root).resolve()
            if out == game or game in out.parents:
                raise ValueError('Refusing writes inside game directory')


def save_report(path, report):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def audit(font_path, text_path):
    from fontTools.ttLib import TTFont
    font = TTFont(font_path)
    cmap = font.getBestCmap()
    if cmap is None:
        raise ValueError('Font has no usable Unicode cmap')
    rows = load_rows(text_path)
    chars = {ord(c) for row in rows for c in row['text'] if ord(c) >= 32}
    missing = chars - set(cmap)
    report = {'font_sha256': digest(font_path), 'text_sha256': digest(text_path),
              'rows': len(rows), 'cmap_entries': len(cmap), 'missing_count': len(missing),
              'affected_rows': sum(any(ord(c) in missing for c in r['text']) for r in rows),
              'missing': [{'char': chr(cp), 'codepoint': f'U+{cp:04X}'} for cp in sorted(missing)],
              'sample_affected_ids': [r.get('id') for r in rows if any(ord(c) in missing for c in r['text'])][:20],
              'font_type': 'TrueType glyf' if 'glyf' in font else 'Other; use appropriate tooling',
              'coverage_complete': not missing, 'visual_uniformity_verified': False,
              'in_game_verified': False}
    font.close()
    return report


def unify(font_path, donor_path, text_path, output_path, report_path, weight=400, game_roots=()):
    from fontTools.ttLib import TTFont
    from fontTools import subset
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.ttLib.scaleUpem import scale_upem
    from PIL import ImageFont
    safe_outputs([output_path, report_path], [font_path, donor_path, text_path], game_roots)
    original = TTFont(font_path); donor = TTFont(donor_path)
    if 'glyf' not in original or 'glyf' not in donor:
        raise ValueError('This helper only supports glyf TrueType fonts, not CFF or game atlases')
    original_cmap = original.getBestCmap()
    if original_cmap is None:
        raise ValueError('Original font has no Unicode cmap')
    original_cmap = original_cmap.copy()
    order = original.getGlyphOrder()[:]
    old_ids = {name: i for i, name in enumerate(order)}
    metrics = original['hmtx'].metrics.copy()
    outlines = {n: original['glyf'][n].compile(original['glyf']) for n in order}
    line_metrics = {k: getattr(original['hhea'], k) for k in ('ascent', 'descent', 'lineGap')}
    rows = load_rows(text_path)
    chars = {ord(c) for row in rows for c in row['text'] if ord(c) >= 32}
    missing = chars - set(original_cmap)
    han = {cp for cp in chars | set(original_cmap) if is_han(cp)}
    required = han | missing
    donor_cmap = donor.getBestCmap() or {}
    uncovered = required - set(donor_cmap)
    if uncovered:
        raise ValueError(f'Donor lacks {len(uncovered)} required characters; first: U+{min(uncovered):04X}')
    cmap_formats = {t.format for t in original['cmap'].tables if t.isUnicode()}
    if any(cp > 0xFFFF for cp in required) and not cmap_formats & {12, 13}:
        raise ValueError('Original Unicode cmap cannot represent supplementary characters; check engine support first')
    opts = subset.Options(); opts.layout_features = []; opts.hinting = False
    sub = subset.Subsetter(options=opts); sub.populate(unicodes=required); sub.subset(donor)
    variable_weight = None
    if 'fvar' in donor:
        axes = {a.axisTag: a.defaultValue for a in donor['fvar'].axes}
        if 'wght' in axes:
            axis = next(a for a in donor['fvar'].axes if a.axisTag == 'wght')
            if not axis.minValue <= weight <= axis.maxValue:
                raise ValueError('Requested weight lies outside donor axis range')
            axes['wght'] = weight; variable_weight = weight
        donor = instantiateVariableFont(donor, axes, inplace=True)
    scale_upem(donor, original['head'].unitsPerEm)
    mapping = {name: 'uniform_han_'+name for name in donor.getGlyphOrder()}
    if len(order) + len(mapping) > 65535:
        raise ValueError('Combined font exceeds TrueType glyph ID capacity')
    for name, new_name in mapping.items():
        if new_name in original['glyf'].glyphs:
            raise ValueError('Glyph naming collision; use unmodified original font')
        glyph = deepcopy(donor['glyf'][name]); glyph.removeHinting()
        if glyph.isComposite():
            for component in glyph.components:
                component.glyphName = mapping[component.glyphName]
        original['glyf'].glyphs[new_name] = glyph
        original['hmtx'].metrics[new_name] = donor['hmtx'].metrics[name]
    original.setGlyphOrder(order + [mapping[n] for n in donor.getGlyphOrder()])
    added = {cp: mapping[n] for cp, n in donor.getBestCmap().items() if cp in required}
    for table in original['cmap'].tables:
        if table.isUnicode():
            for cp, name in added.items():
                if cp <= 0xFFFF or table.format in (12, 13):
                    table.cmap[cp] = name
    output = Path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    original.save(output)
    fixed = TTFont(output, checkChecksums=2); cmap = fixed.getBestCmap(); fixed_order = fixed.getGlyphOrder()
    checks = {
        'coverage_complete': chars <= set(cmap),
        'all_han_same_donor': all(fixed.getGlyphID(cmap[cp]) == original.getGlyphID(added[cp]) for cp in han),
        'original_non_han_cmap_preserved': all(fixed.getGlyphID(cmap[cp]) == old_ids[n] for cp, n in original_cmap.items() if not is_han(cp)),
        'original_glyph_metrics_preserved': all(fixed['hmtx'].metrics[fixed_order[i]] == metrics[n] for i, n in enumerate(order)),
        'original_glyph_outlines_preserved': all(fixed['glyf'][fixed_order[i]].compile(fixed['glyf']) == outlines[n] for i, n in enumerate(order)),
        'line_metrics_preserved': all(getattr(fixed['hhea'], k) == v for k, v in line_metrics.items()),
        'han_advance_widths_preserved': all(fixed['hmtx'].metrics[cmap[cp]][0] == metrics[n][0] for cp, n in original_cmap.items() if is_han(cp)),
        'font_family_names_preserved': fixed['name'].compile(fixed) == original['name'].compile(original),
    }
    render = ImageFont.truetype(str(output), 32)
    checks['all_han_rasterize_nonempty'] = all(render.getmask(chr(cp)).getbbox() is not None for cp in han)
    report = {'original_sha256': digest(font_path), 'donor_sha256': digest(donor_path),
              'text_sha256': digest(text_path), 'output_sha256': digest(output),
              'uniform_han_count': len(han), 'missing_before': len(missing),
              'missing_after': len(chars-set(cmap)), 'requested_weight': weight,
              'applied_variable_weight': variable_weight,
              'static_donor_weight_note': None if variable_weight is not None else 'Existing donor weight used; no wght change',
              'units_per_em': fixed['head'].unitsPerEm, 'checks': checks,
              'offline_passed': all(checks.values()), 'in_game_verified': False, 'game_written': False}
    save_report(report_path, report)
    if not report['offline_passed']:
        failed = [k for k, passed in checks.items() if not passed]
        raise ValueError('Do not package this font: '+', '.join(failed))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    for mode in ('audit', 'unify'):
        s = sub.add_parser(mode); s.add_argument('--font', required=True)
        s.add_argument('--text-json', required=True); s.add_argument('--report', required=True)
        s.add_argument('--game-root', action='append', default=[])
        if mode == 'unify':
            s.add_argument('--donor', required=True); s.add_argument('--output', required=True)
            s.add_argument('--weight', type=float, default=400)
    a = p.parse_args()
    if a.mode == 'audit':
        safe_outputs([a.report], [a.font, a.text_json], a.game_root)
        r = audit(a.font, a.text_json); save_report(a.report, r)
        summary = {k: r[k] for k in ('rows','missing_count','affected_rows','coverage_complete')}
    else:
        r = unify(a.font, a.donor, a.text_json, a.output, a.report, a.weight, a.game_root)
        summary = {k: r[k] for k in ('uniform_han_count','missing_before','missing_after','offline_passed','in_game_verified')}
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == '__main__':
    main()
