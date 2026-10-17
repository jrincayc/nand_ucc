import json, subprocess, sys, os, multiprocessing as mp, re
BIN = '/home/claude/rndw/target/release/mutrun'
def one(info):
    n = info['name']
    if not os.path.exists(f'mut/{n}.cmds'):
        info['out'] = f"no_run: parent status {info['status']}"; return info
    try:
        o = subprocess.run([BIN, 'child', f'mut/{n}.cmds', f'mut/{n}.rom'], capture_output=True, text=True, timeout=900).stdout
    except subprocess.TimeoutExpired:
        o = 'result: HARNESS_TIMEOUT'
    info['out'] = o.strip(); return info
if __name__ == '__main__':
    items = json.load(open('mut_sample.json'))
    res = []
    with mp.Pool(2) as pool:
        for k, r in enumerate(pool.imap_unordered(one, items)):
            res.append(r); json.dump(res, open('mut_results.json', 'w'))
            if (k + 1) % 10 == 0: print(k + 1, flush=True)
