#!/usr/bin/env python3
"""语料校验脚本 —— 把内容判真法则变成 CI 可跑的门禁。

规则来源：docs/content-guidelines.md
用法：python3 scripts/validate_corpus.py [--data-dir data]
退出码：0 = 全部通过；1 = 存在 ERROR（阻塞发布）；WARN 不阻塞但会打印。
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CONFIDENCE_LEVELS = {'L1', 'L2', 'L3', 'L4', 'L5'}
STILL_EXISTS_VALUES = {'open', 'restricted', 'closed', 'uncertain', 'relocated'}
ASSOC_TYPES = {'person', 'work', 'film', 'screen', 'event'}
# 三字段：判真法则的核心。缺一即应降为 L4。
REQUIRED_TRIPLE = ('why_here', 'when', 'detail')

errors = []
warnings = []


def err(where, msg):
    errors.append(f'{where}: {msg}')


def warn(where, msg):
    warnings.append(f'{where}: {msg}')


def domain_of(url):
    m = re.match(r'https?://([^/]+)', url or '')
    if not m:
        return None
    host = m.group(1).lower()
    return host[4:] if host.startswith('www.') else host


def check_pois(pois):
    ids = Counter(p.get('id') for p in pois)
    for pid, n in ids.items():
        if n > 1:
            err('pois', f'id 重复 {n} 次: {pid}')
        if not pid:
            err('pois', '存在缺 id 的 POI')

    for p in pois:
        pid = p.get('id', '<no-id>')
        w = f'pois/{pid}'

        for f in ('name_zh', 'name_fr', 'address', 'era', 'still_exists'):
            if p.get(f) in (None, ''):
                err(w, f'缺必填字段 {f}')

        se = p.get('still_exists')
        if se and se not in STILL_EXISTS_VALUES:
            err(w, f'still_exists 取值非法: {se}（允许 {sorted(STILL_EXISTS_VALUES)}）')
        if se in ('closed', 'uncertain', 'relocated') and not p.get('access_note'):
            warn(w, f'still_exists={se} 但无 access_note 说明')

        era = p.get('era')
        if era is not None and not (isinstance(era, int) and 1 <= era <= 7):
            err(w, f'era 应为 1–7 的整数，实际 {era!r}')

        # 坐标：缺失不阻塞（地理编码是独立步骤），但必须被看见
        c = p.get('coordinates')
        if not c:
            warn(w, '缺 coordinates（上线前需地理编码）')
        elif not (isinstance(c, (list, tuple)) and len(c) == 2):
            err(w, f'coordinates 应为 [lng, lat]，实际 {c!r}')
        else:
            lng, lat = c
            # 巴黎大区粗边界，挡住经纬度写反这类典型错误
            if not p.get('outside_paris'):
                if not (1.4 <= lng <= 3.6):
                    err(w, f'经度 {lng} 不在巴黎大区范围（是否与纬度写反？）')
                if not (48.1 <= lat <= 49.3):
                    err(w, f'纬度 {lat} 不在巴黎大区范围（是否与经度写反？）')

        assocs = p.get('associations') or []
        if not assocs:
            warn(w, '无任何 association')

        for i, a in enumerate(assocs):
            aw = f'{w}/assoc[{i}]'
            aname = a.get('name') or '<无名>'

            if a.get('type') not in ASSOC_TYPES:
                err(aw, f'type 非法: {a.get("type")!r}（允许 {sorted(ASSOC_TYPES)}）')

            conf = a.get('confidence')
            if conf not in CONFIDENCE_LEVELS:
                err(aw, f'confidence 非法: {conf!r}')

            # ★ 判真法则的机器执行：三字段缺一 → 必须已降为 L4（或本就是 L5 辟谣素材）
            missing = [f for f in REQUIRED_TRIPLE if not a.get(f)]
            if missing:
                if conf not in ('L4', 'L5'):
                    err(aw, f'「{aname}」缺 {missing}，按判真法则必须降为 L4，实际为 {conf}')
                else:
                    warn(aw, f'「{aname}」缺 {missing}，已按规则降为 {conf} ✓')

            srcs = a.get('sources') or []
            if not srcs:
                err(aw, f'「{aname}」无任何 sources')
                continue

            doms = [domain_of(s) for s in srcs]
            uniq = {d for d in doms if d}
            # 独立源判定：同域名不同页不算两个独立源
            if conf in ('L1', 'L2') and len(uniq) < 2:
                err(aw, f'「{aname}」标为 {conf} 但只有 {len(uniq)} 个独立域名 '
                        f'（{sorted(uniq)}）；L1/L2 需 ≥2 个独立源')
            if conf == 'L3' and len(uniq) > 1:
                warn(aw, f'「{aname}」标为 L3（只有一个出处）但有 {len(uniq)} 个域名，'
                         f'请复核是否可升级')
            if len(doms) > len(uniq):
                warn(aw, f'「{aname}」sources 含同域名多页，独立源实际只有 {len(uniq)} 个')


def check_storylines(sl_doc, pois):
    lines = sl_doc.get('storylines') if isinstance(sl_doc, dict) else sl_doc
    if not lines:
        err('storylines', '未找到 storylines 列表')
        return set()

    poi_ids = {p.get('id') for p in pois}
    declared = set()
    seen = Counter()

    for l in lines:
        lid = l.get('id', '<no-id>')
        w = f'storylines/{lid}'
        seen[lid] += 1
        declared.add(lid)

        for f in ('id', 'theme_zh', 'theme_en', 'persona_code'):
            if not l.get(f):
                err(w, f'缺必填字段 {f}')

        status = l.get('corpus_status')
        if status not in ('complete', 'pending'):
            err(w, f'corpus_status 取值非法: {status!r}（允许 complete / pending）')

        stations = l.get('stations') or []
        # pending 线允许 stations 为空——不编造站点，这是内容红线
        if status == 'complete' and not stations:
            err(w, 'corpus_status=complete 但 stations 为空')
        if status == 'pending' and stations:
            warn(w, f'corpus_status=pending 但已有 {len(stations)} 站，请复核状态')

        orders = []
        for j, s in enumerate(stations):
            sw = f'{w}/station[{j}]'
            if not isinstance(s, dict):
                err(sw, f'站点应为对象，实际 {type(s).__name__}')
                continue
            pid = s.get('poi_id')
            if not pid:
                err(sw, '缺 poi_id')
            elif pid not in poi_ids:
                err(sw, f'poi_id {pid} 在 pois.json 中不存在')
            o = s.get('order')
            if not isinstance(o, int):
                err(sw, f'order 应为整数，实际 {o!r}')
            else:
                orders.append(o)

        if orders and sorted(orders) != list(range(1, len(orders) + 1)):
            err(w, f'order 应为从 1 开始的连续整数，实际 {sorted(orders)}')

    for lid, n in seen.items():
        if n > 1:
            err('storylines', f'id 重复 {n} 次: {lid}')

    # 反向：POI 声明的线必须真实存在，且该线应确实收录该 POI
    line_stations = {l.get('id'): {s.get('poi_id') for s in (l.get('stations') or [])
                                   if isinstance(s, dict)}
                     for l in lines}
    for p in pois:
        for lid in (p.get('storylines') or []):
            if lid not in declared:
                err(f'pois/{p.get("id")}', f'引用了不存在的故事线 {lid}')
            elif p.get('id') not in line_stations.get(lid, set()):
                err(f'pois/{p.get("id")}', f'声明属于 {lid}，但该线 stations 里没有它'
                                           f'（双向引用不一致）')

    return declared


def check_personas(doc, declared_lines):
    ps = doc.get('personas') if isinstance(doc, dict) else doc
    if not ps:
        err('personas', '未找到 personas 列表')
        return
    if len(ps) != 16:
        err('personas', f'人格数应为 16（4 维度 × 二分），实际 {len(ps)}')

    codes = Counter(p.get('code') for p in ps)
    for c, n in codes.items():
        if n > 1:
            err('personas', f'code 重复 {n} 次: {c}')

    dims = ('culture', 'planning', 'social', 'spending')
    combos = Counter()
    used_lines = Counter()

    for p in ps:
        code = p.get('code', '<no-code>')
        w = f'personas/{code}'
        for d in dims:
            if p.get(d) not in ('high', 'low'):
                err(w, f'维度 {d} 应为 high / low，实际 {p.get(d)!r}')
        combos[tuple(p.get(d) for d in dims)] += 1

        lid = p.get('storyline_id')
        if not lid:
            err(w, '缺 storyline_id')
        elif declared_lines and lid not in declared_lines:
            err(w, f'storyline_id {lid} 不存在')
        else:
            used_lines[lid] += 1

    # 16 种人格必须是 4 维二分的完整笛卡尔积，不重不漏
    for combo, n in combos.items():
        if n > 1:
            err('personas', f'维度组合重复 {n} 次: {dict(zip(dims, combo))}')
    if len(combos) != 16:
        err('personas', f'4 维二分应产生 16 种唯一组合，实际 {len(combos)} 种')

    # 主题为主体、人格为标签：一条线一个人格，不该多个人格指向同一条线
    for lid, n in used_lines.items():
        if n > 1:
            err('personas', f'{n} 个人格都指向 {lid}——应为一线一人格')


def check_debunks(doc, pois):
    ds = doc.get('debunks') if isinstance(doc, dict) else doc
    if not ds:
        warn('debunks', '未找到 debunks 列表')
        return
    poi_ids = {p.get('id') for p in pois}
    # pois.json 里实际存在的 L5 关联，用于核对索引是否同步
    l5_pois = {p['id'] for p in pois
               for a in (p.get('associations') or [])
               if a.get('confidence') == 'L5'}
    linked = set()

    for d in ds:
        did = d.get('id', '<no-id>')
        w = f'debunks/{did}'
        for f in ('title_zh', 'official_claim', 'reality', 'status'):
            if not d.get(f):
                err(w, f'缺必填字段 {f}')

        st = d.get('status')
        if st == 'linked':
            pid = d.get('poi_id')
            if not pid:
                err(w, 'status=linked 但无 poi_id')
            elif pid not in poi_ids:
                err(w, f'poi_id {pid} 在 pois.json 中不存在')
            else:
                linked.add(pid)
                if pid not in l5_pois:
                    err(w, f'声明 linked 到 {pid}，但该 POI 的 associations 里没有 '
                           f'confidence=L5 的条目（索引与事实源不一致）')
        elif st == 'pending_poi':
            if d.get('poi_id'):
                warn(w, 'status=pending_poi 但填了 poi_id')
        else:
            err(w, f'status 取值非法: {st!r}（允许 linked / pending_poi）')

    for pid in sorted(l5_pois - linked):
        warn('debunks', f'POI {pid} 有 L5 素材但未被 debunks.json 索引')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default=None)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    data_dir = Path(args.data_dir) if args.data_dir else root / 'data'

    def load(name, required=True):
        p = data_dir / name
        if not p.exists():
            (err if required else warn)('files', f'{name} 不存在')
            return None
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            err('files', f'{name} JSON 解析失败: {e}')
            return None

    pois = load('pois.json') or []
    storylines = load('storylines.json')
    personas = load('personas.json')
    debunks = load('debunks.json', required=False)

    declared = set()
    if pois:
        check_pois(pois)
    if storylines is not None:
        declared = check_storylines(storylines, pois)
    if personas is not None:
        check_personas(personas, declared)
    if debunks is not None:
        check_debunks(debunks, pois)

    # ---- 汇总 ----
    n_assoc = sum(len(p.get('associations') or []) for p in pois)
    conf = Counter(a.get('confidence') for p in pois
                   for a in (p.get('associations') or []))
    print(f'POI {len(pois)} 个，关联 {n_assoc} 条')
    print('置信度分布: ' + '  '.join(f'{k}={conf[k]}' for k in sorted(conf) if k))

    if warnings:
        print(f'\n--- WARN ({len(warnings)}) ---')
        for x in warnings:
            print(f'  ⚠ {x}')
    if errors:
        print(f'\n--- ERROR ({len(errors)}) ---')
        for x in errors:
            print(f'  ✗ {x}')
        print(f'\n校验未通过：{len(errors)} 个 ERROR')
        return 1

    print(f'\n校验通过{f"（{len(warnings)} 个 WARN 不阻塞）" if warnings else ""}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
