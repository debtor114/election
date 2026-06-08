# -*- coding: utf-8 -*-
"""
T3 — 투표율 × 승자 득표율 포렌식 (Shpilkin류)
읍면동별 (투표율, 승자 득표율) 산점도 + 2D 히스토그램을 저장하고,
고투표율 꼬리에서 승자 득표율이 비정상적으로 상승하는지 정량화한다.

지표:
  - tail_corr : 투표율 상위 50% 구간의 (투표율, 승자득표율) 피어슨 상관
  - lift      : 투표율 상위 10% 평균 승자득표율 − 전체 평균
판정(FLAG): tail_corr > 0.45 그리고 lift > 0.05 (둘 다일 때만; 단독은 약함).
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
# 한글 폰트 (Windows: 맑은 고딕)
for _f in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    try:
        matplotlib.rcParams["font.family"] = _f
        break
    except Exception:
        pass
matplotlib.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import necdata as nd

TAIL_CORR_FLAG = 0.45
LIFT_FLAG = 0.05
OUT = Path(__file__).resolve().parent.parent / "out"


def collect(df, election_type):
    """모든 race의 읍면동 (투표율, 승자득표율) 점들."""
    xs, ys = [], []
    per_race = []
    for key, race in nd.iter_races(df, election_type):
        cc = nd.cand_cols(race)
        if not cc:
            continue
        u = nd.units(race, nd.GUBUN_SUBTOTAL)  # 읍면동 '계'
        if len(u) < 5:
            continue
        win = race[cc].sum().idxmax()
        elec = u["선거인수"].replace(0, np.nan)
        valid = u[nd.TOTAL_COL].replace(0, np.nan)
        turnout = (u["투표수"] / elec).to_numpy()
        wshare = (u[win] / valid).to_numpy()
        m = np.isfinite(turnout) & np.isfinite(wshare)
        turnout, wshare = turnout[m], wshare[m]
        xs.extend(turnout); ys.extend(wshare)
        if m.sum() >= 8:
            per_race.append((nd.race_label(key), turnout, wshare))
    return np.array(xs), np.array(ys), per_race


def tail_metrics(x, y):
    if len(x) < 10:
        return float("nan"), float("nan")
    med = np.median(x)
    tail = x >= med
    if tail.sum() >= 5 and np.std(x[tail]) > 0:
        tail_corr = float(np.corrcoef(x[tail], y[tail])[0, 1])
    else:
        tail_corr = float("nan")
    thr = np.quantile(x, 0.9)
    lift = float(y[x >= thr].mean() - y.mean())
    return tail_corr, lift


def save_plot(x, y, election_type):
    OUT.mkdir(exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].scatter(x * 100, y * 100, s=6, alpha=0.3)
    ax[0].set_xlabel("투표율 %"); ax[0].set_ylabel("승자 득표율 %")
    ax[0].set_title(f"{election_type} — 읍면동 산점도")
    h = ax[1].hist2d(x * 100, y * 100, bins=40, cmap="viridis")
    fig.colorbar(h[3], ax=ax[1]); ax[1].set_xlabel("투표율 %"); ax[1].set_ylabel("승자 득표율 %")
    ax[1].set_title("2D 히스토그램")
    fig.tight_layout()
    fp = OUT / f"T3_{election_type}.png"
    fig.savefig(fp, dpi=110); plt.close(fig)
    return fp


def run(df, election_type, plot=True):
    x, y, _ = collect(df, election_type)
    if len(x) < 10:
        return None
    tail_corr, lift = tail_metrics(x, y)
    fp = save_plot(x, y, election_type) if plot else None
    flag = (np.isfinite(tail_corr) and tail_corr > TAIL_CORR_FLAG and lift > LIFT_FLAG)
    return {
        "test": "T3", "race": f"{election_type}(전체)", "n_units": len(x),
        "tail_corr": round(tail_corr, 3), "lift": round(lift, 3),
        "plot": str(fp) if fp else "",
        "verdict": "FLAG" if flag else "PASS",
    }


def main():
    etype = sys.argv[1] if len(sys.argv) > 1 else "시도지사"
    df = nd.load_type(etype)
    res = run(df, etype)
    print(f"[T3 투표율포렌식] {etype}")
    if not res:
        print("  표본 부족"); return
    print(f"  읍면동 {res['n_units']}개  꼬리상관={res['tail_corr']}  lift={res['lift']}"
          f"  → {res['verdict']}")
    print(f"  플롯: {res['plot']}")


if __name__ == "__main__":
    main()
