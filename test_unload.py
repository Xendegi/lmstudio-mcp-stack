"""test_unload.py - the witness stone for lmstudio_manager's load/unload (2026-10-05).

Written because the old unload was wrong in three ways that a green "nothing
raised" test cannot see. Every case below is a real defect reproduced against
the real server, and every fix is asserted by behaviour, not by inspection.

  python test_unload.py            # live server, real models
  python test_unload.py --offline  # logic-only, no network

Gates:
  1. RESOLVE  - instance ids come from the LIVE list, never the cache
  2. STALE    - a poisoned `:<n>` cache cannot cause a 404 (the exact 2026-10-05 bug)
  3. VERIFY   - ok:true only after the instance is provably gone
  4. NOOP     - unloading nothing is a clean, honest no-op (not a bare 404)
  5. IDEMPOT  - a second unload is honest, not a crash
  6. PROTECT  - the embedder the memory port needs is never unloaded by accident
  7. NOLIES   - the manager's reported state matches the server's truth
"""

import importlib.util
import sys
import time

# This console is CP1256 and cannot print the section glyphs below (the same
# class of bug the reflex hit on 2026-10-04). Reconfigure once, never raise.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

OFFLINE = '--offline' in sys.argv
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print(f'  {"ok  " if ok else "FAIL"}  {name}' + (f' - {detail}' if detail else ''))
    return bool(ok)


def load_mod():
    spec = importlib.util.spec_from_file_location('lmgr', 'lmstudio_manager.py')
    m = importlib.util.module_from_spec(spec)
    sys.modules['lmgr'] = m
    spec.loader.exec_module(m)
    return m


m = load_mod()
SMALL = 'qwen3-8b'          # ~5GB, fast to load and to drain
EMBED = 'text-embedding-nomic-embed-text-v1.5'


def gpu_mb():
    try:
        import subprocess
        r = subprocess.run(['nvidia-smi', '--query-gpu=memory.used',
                            '--format=csv,noheader,nounits'],
                           capture_output=True, text=True, timeout=30)
        return int(r.stdout.strip().splitlines()[0])
    except Exception:
        return -1


def main():
    print('test_unload - witness stone for lmstudio_manager load/unload\n')

    if OFFLINE:
        print('▸ OFFLINE: shape assertions only (no server)')
        src = open('lmstudio_manager.py', encoding='utf-8').read()
        check('exactly one unload_model_internal definition',
              src.count('def unload_model_internal') == 1)
        check('exactly one live_loaded_instances definition',
              src.count('def live_loaded_instances') == 1)
        body = src.split('def unload_model_internal')[1].split('\ndef ')[0]
        # Strip the docstring before asserting on shape: the docstring itself
        # uses the words this check greps for, so an un-stripped search reports
        # a false failure. (Same class of error as the reflex's mute-switch
        # check - the check was blunter than the truth.)
        import re as _re
        code = _re.sub(r'"""[\s\S]*?"""', '', body)
        code = '\n'.join(l.split('#')[0] for l in code.splitlines())
        live_at = code.find('live_loaded_instances(')
        post_at = code.find('try_endpoints(')
        check('unload resolves live instances BEFORE any POST',
              live_at != -1 and (post_at == -1 or live_at < post_at),
              f'live@{live_at} post@{post_at}')
        check('unload polls for drain before reporting ok',
              'wait_for_instance_gone' in body)
        check('unload no longer reads the cached id as its source of truth',
              'instance_id = state.get("loaded_instance_id")' not in body)
        report()
        return

    print('▸ 0. ground truth from the server')
    live0 = m.live_loaded_instances()
    print(f'   resident at start: {[(i["id"], i["type"]) for i in live0]}')
    # The embedder is LAZY: LM Studio's auto_unload_aux (60s, per the manager
    # config) drops it when idle, and embed.py loads it on demand. So its
    # absence at start is NORMAL, not a fault - asserting it resident made this
    # gate fail for the wrong reason. What matters is that unload never takes
    # it DOWN; gate 6 tests that with whatever is resident at the time.
    embed_before = any(i['id'] == EMBED for i in live0)
    print(f'   embedder resident at start: {embed_before} '
          f'(lazy-loaded; absence is normal)')

    print('\n▸ 1-4. NOLIES + NOOP: unload everything, honestly')
    t0 = time.time()
    res = m.unload_model_internal(None)
    dt = time.time() - t0
    print(f'   result ok={res.get("ok")} verified={res.get("verified")} '
          f'unloaded={len(res.get("unloaded", []))} note={res.get("note")} ({dt:.1f}s)')
    for u in res.get('unloaded', []):
        print(f'     {u["instance_id"]:28} verified={u["verified"]} '
              f'drain={u["drain_seconds"]}s http={u["http_status"]}')
    check('unload reports ok', res.get('ok') is True)
    check('unload reports verified (drain-aware)', res.get('verified') is True)
    check('every unload was verified gone',
          all(u['verified'] for u in res.get('unloaded', [])), str(res.get('unloaded')))
    check('no failures reported', not res.get('failed'), str(res.get('failed')))

    after = m.live_loaded_instances()
    llms = [i for i in after if i['type'] != 'embedding']
    check('no llm instance remains resident', not llms, str(llms))
    check('unload result agrees with the server (no lying)',
          len(llms) == len([i for i in res.get('still_loaded', []) if i.get('type') != 'embedding']),
          f'live llms={len(llms)} reported={len(res.get("still_loaded", []))}')

    print('\n▸ 5. IDEMPOT: unload again with nothing loaded')
    res2 = m.unload_model_internal(None)
    print(f'   result ok={res2.get("ok")} note={res2.get("note")}')
    check('second unload is a clean ok, not an error', res2.get('ok') is True)
    check('second unload says plainly that no llm was loaded',
          'no llm model was loaded' in str(res2.get('note', '')), str(res2.get('note')))
    check('second unload is not a bare 404',
          res2.get('status') is None, str(res2.get('status')))

    print('\n▸ 6. PROTECT: an unnamed unload must NEVER take the embedder down')
    # Two different gates, because they prove different things.
    #
    # 6a is a UNIT gate on the filter: the embedder's residency in this house
    # is owned by another process (the memory port's embed.py loads it on
    # demand, and auto_unload_aux drops it 60s later), so asserting on live
    # residency proved nothing but flakiness. Instead the source of truth is
    # stubbed with both kinds present, and the call must refuse the embedder.
    real_live = m.live_loaded_instances
    m.live_loaded_instances = lambda name=None: (
        [{'id': 'fake-llm', 'model_key': 'fake-llm', 'type': 'llm', 'display_name': 'fake'}] +
        [{'id': 'fake-embedder', 'model_key': EMBED, 'type': 'embedding', 'display_name': EMBED}]
    ) if name is None else real_live(name)
    posted = []
    real_try = m.try_endpoints
    m.try_endpoints = lambda meth, eps, payload=None, timeout=None: (
        posted.append(payload), (eps[0] if eps else None, m.HttpResult(ok=True, status=200, data={}))
    )[1] if payload else real_try(meth, eps, payload=payload, timeout=timeout)
    res_p = m.unload_model_internal(None)
    m.live_loaded_instances = real_live
    m.try_endpoints = real_try
    ids_posted = [p.get('instance_id') for p in posted if p]
    print(f'   POSTed instance ids: {ids_posted}')
    check('unnamed unload never POSTs an embedding instance',
          not any('embed' in str(i).lower() for i in ids_posted), str(ids_posted))
    check('unnamed unload still POSTs every llm', 'fake-llm' in ids_posted, str(ids_posted))

    # 6b is the OBSERVED gate, reported but not asserted: residency here is
    # another process's business, and a failure here would be its news, not
    # this function's.
    emb_res = [i for i in real_live() if i['type'] == 'embedding']
    print(f'   observed embedders resident right now: {[i["id"] for i in emb_res]}'
          f'  (owned by embed.py + auto_unload_aux, not asserted)')

    print('\n▸ 7. RESOLVE + STALE: poison the cache with the dead ":<n>" id')
    st = m.get_state()
    poisoned = dict(st)
    poisoned['loaded_instance_id'] = 'qwen3-8b:2'      # exactly the 2026-10-05 value
    poisoned['loaded_model_name'] = 'qwen/qwen3.5-9b'
    m.save_state(poisoned)
    live_now = m.live_loaded_instances()
    print(f'   server says resident: {[(i["id"]) for i in live_now]}')
    print(f'   cache says          : {m.get_state().get("loaded_instance_id")}')
    res3 = m.unload_model_internal(None)
    check('stale cached id does not produce a failure',
          res3.get('ok') is True, str(res3.get('error')))
    check('stale cached id does not produce a 404', res3.get('status') is None,
          str(res3.get('status')))
    check('stale cache was reported, not silently trusted',
          'stale_cached_instance_id' in res3 or not m.live_loaded_instances())

    print('\n▸ 8. LOAD -> UNLOAD round trip on a real model')
    if m.model_exists(SMALL):
        g0 = gpu_mb()
        ld = m.load_model_internal(SMALL)
        print(f'   load ok={ld.get("ok")} instance_id={ld.get("instance_id")} '
              f'verified={ld.get("verified")}')
        check('load succeeds', ld.get('ok') is True)
        check('load reports the server-minted instance id',
              ld.get('instance_id') == SMALL, str(ld.get('instance_id')))
        check('cache now holds the LIVE instance id',
              m.get_state().get('loaded_instance_id') == SMALL,
              str(m.get_state().get('loaded_instance_id')))
        time.sleep(4)
        g1 = gpu_mb()
        print(f'   gpu {g0} -> {g1} MB while loaded')
        check('gpu memory actually rose on load', g1 > g0, f'{g0} -> {g1}')

        un = m.unload_model_internal(SMALL)
        print(f'   unload ok={un.get("ok")} verified={un.get("verified")} '
              f'drain={[u["drain_seconds"] for u in un.get("unloaded", [])]}')
        check('targeted unload works', un.get('ok') is True, str(un.get('error')))
        check('targeted unload verified the instance left',
              all(u['verified'] for u in un.get('unloaded', [])))
        check('the model is genuinely gone',
              not any(i['id'] == SMALL for i in m.live_loaded_instances()))
        time.sleep(4)
        g2 = gpu_mb()
        print(f'   gpu {g1} -> {g2} MB after unload')
        check('gpu memory actually fell on unload', g2 < g1, f'{g1} -> {g2}')
        emb_now = [i['id'] for i in m.live_loaded_instances() if i['type'] == 'embedding']
        print(f'   embedders resident after the cycle: {emb_now or "none"} '
              f'(reported only - residency is embed.py\'s business, see gate 6)')
    else:
        check(f'{SMALL} exists', False, 'model not found - round trip skipped')

    print('\n▸ 9. final truth')
    fin = m.live_loaded_instances()
    print(f'   resident: {[(i["id"], i["type"]) for i in fin]}')
    st = m.get_state()
    print(f'   cache   : model={st.get("loaded_model_name")} instance={st.get("loaded_instance_id")}')
    # Read the cache AFTER the live read: auto_unload_aux (60s) can free an llm
    # in between, and then a cache that was correct becomes "stale" by timing
    # alone. Ordering the reads this way makes the assertion meaningful.
    check('cache never claims an embedding model as the loaded model',
          st.get('loaded_instance_id') != EMBED, str(st.get('loaded_instance_id')))
    fresh = m.live_loaded_instances()
    fresh_llm = [i for i in fresh if i['type'] != 'embedding']
    st2 = m.get_state()
    check('cache instance id matches the server after any unload',
          (st2.get('loaded_instance_id') or None) == (fresh_llm[0]['id'] if fresh_llm else None),
          f'cache={st2.get("loaded_instance_id")} server={fresh_llm[0]["id"] if fresh_llm else None}')

    report()


def report():
    failed = [n for n, ok in RESULTS if not ok]
    print(f'\n{"FAILED" if failed else "PASS"} - {len(RESULTS) - len(failed)}/{len(RESULTS)} checks green')
    if failed:
        for n in failed:
            print(f'   FAILED: {n}')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()