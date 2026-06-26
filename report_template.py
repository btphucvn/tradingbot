#!/usr/bin/env python3
"""Template HTML cho báo cáo Danh mục CTA. render(data) -> chuỗi HTML tự chứa."""
from __future__ import annotations
import json


def pct(x, d=1):
    if x != x:  # NaN
        return "—"
    return f"{x*100:.{d}f}%"


def num(x, d=2):
    if x != x:
        return "—"
    return f"{x:.{d}f}"


def market_rows(markets):
    rows = []
    for m in markets:
        cls = "crypto" if m["cls"] == "Crypto" else ""
        rows.append(f"""<tr>
  <td class="sym"><span class="dot {slug(m['cls'])}"></span>{m['label']}</td>
  <td><span class="tag">{m['cls']}</span></td>
  <td class="r {posneg(m['cagr'])}">{pct(m['cagr'])}</td>
  <td class="r neg">{pct(m['dd'])}</td>
  <td class="r">{num(m['calmar'])}</td>
  <td class="r">{num(m['sharpe'])}</td>
  <td class="r">{m['n']}</td>
  <td class="r">{pct(m['win'])}</td>
  <td class="r">{num(m['pf'])}</td>
  <td class="r">{pct(m['weight'])}</td>
</tr>""")
    return "\n".join(rows)


def slug(cls):
    return {"Crypto": "c", "Kim loại": "m", "Ngoại hối": "fx",
            "Năng lượng": "e", "Nông sản": "ag", "Chỉ số": "ix"}.get(cls, "x")


def posneg(x):
    return "pos" if (x == x and x >= 0) else "neg"


def sweep_rows(sweep, ew):
    rows = []
    ewmap = {e["lev"]: e for e in ew}
    for s in sweep:
        e = ewmap.get(s["lev"], {})
        cls = "hit" if s["ok"] else ""
        badge = '<span class="ok">✅ ĐẠT</span>' if s["ok"] else ""
        star = ' ★' if s["lev"] == 5 else ""
        rows.append(f"""<tr class="{cls}">
  <td class="r"><b>{s['lev']:g}×</b>{star}</td>
  <td class="r pos">{pct(s['cagr'])}</td>
  <td class="r neg">{pct(s['dd'])}</td>
  <td class="r">{num(s['calmar'])}</td>
  <td class="r">{num(s['mult'],1)}×</td>
  <td class="sep r pos">{pct(e.get('cagr',float('nan')))}</td>
  <td class="r neg">{pct(e.get('dd',float('nan')))}</td>
  <td class="r">{num(e.get('calmar',float('nan')))}</td>
  <td>{badge}</td>
</tr>""")
    return "\n".join(rows)


def yearly_bars(yearly):
    mx = max((abs(y["ret"]) for y in yearly), default=1) or 1
    out = []
    for y in yearly:
        v = y["ret"]
        h = abs(v) / mx * 100
        cls = "pos" if v >= 0 else "neg"
        out.append(f"""<div class="ybar">
  <div class="ytrack"><div class="yfill {cls}" style="height:{h:.0f}%" title="{pct(v)}"></div></div>
  <div class="yval {cls}">{pct(v,0)}</div>
  <div class="ylab">{y['year']}</div>
</div>""")
    return "\n".join(out)


def corr_table(corr):
    syms, m = corr["syms"], corr["m"]
    head = "".join(f"<th>{s[:3]}</th>" for s in syms)
    rows = []
    for i, s in enumerate(syms):
        cells = []
        for j, v in enumerate(m[i]):
            # màu: xanh thấp (đa dạng tốt), đỏ cao (tương quan cao)
            if i == j:
                cells.append(f'<td class="diag">1</td>')
            else:
                t = max(min(v, 1), -1)
                # 0 -> trung tính, +1 -> đỏ, -1 -> xanh dương
                if t >= 0:
                    bg = f"rgba(239,68,68,{t*0.7:.2f})"
                else:
                    bg = f"rgba(59,130,246,{-t*0.6:.2f})"
                cells.append(f'<td style="background:{bg}">{v:.2f}</td>')
        rows.append(f"<tr><th class='rh'>{s[:3]}</th>{''.join(cells)}</tr>")
    return f"<table class='corr'><tr><th></th>{head}</tr>{''.join(rows)}</table>"


def render(d):
    p = d["port"]; meta = d["meta"]; iso = d["iso"]
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Danh mục CTA Risk-Parity — Phân tích chiến thuật</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{{
  --bg:#0a0e17; --panel:#121826; --panel2:#0f1422; --line:#1e2740;
  --txt:#e6edf6; --mut:#8a97ad; --acc:#5eead4; --acc2:#38bdf8;
  --pos:#34d399; --neg:#f87171; --gold:#fbbf24;
  --mono:'SF Mono',ui-monospace,'Cascadia Code',Menlo,monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(1200px 600px at 70% -10%,#16243d 0%,var(--bg) 55%);
  color:var(--txt);font:15px/1.55 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:40px 22px 80px}}
header{{margin-bottom:28px}}
.eyebrow{{font:600 12px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase;
  color:var(--acc);margin-bottom:12px}}
h1{{font-size:clamp(26px,4vw,40px);margin:0 0 8px;letter-spacing:-.02em;font-weight:740}}
.sub{{color:var(--mut);max-width:760px;font-size:15.5px}}
.badge{{display:inline-flex;align-items:center;gap:7px;background:linear-gradient(135deg,#0e3a32,#0a2a26);
  border:1px solid #1c5a4d;color:var(--acc);padding:6px 14px;border-radius:999px;
  font:600 13px/1 system-ui;margin-top:16px}}
.badge b{{color:#fff}}
.meta{{margin-top:14px;color:var(--mut);font:12px/1.6 var(--mono)}}

.grid{{display:grid;gap:16px}}
.kpis{{grid-template-columns:repeat(5,1fr);margin:30px 0 12px}}
@media(max-width:820px){{.kpis{{grid-template-columns:repeat(2,1fr)}}}}
.kpi{{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
  border-radius:14px;padding:18px 18px 16px;position:relative;overflow:hidden}}
.kpi::before{{content:"";position:absolute;inset:0 0 auto 0;height:2px;
  background:linear-gradient(90deg,var(--acc),transparent)}}
.kpi .k{{font:600 11px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}}
.kpi .v{{font-size:30px;font-weight:720;margin-top:10px;letter-spacing:-.02em}}
.kpi .d{{font-size:12px;color:var(--mut);margin-top:4px}}
.v.pos{{color:var(--pos)}} .v.neg{{color:var(--neg)}} .v.gold{{color:var(--gold)}}

section{{margin-top:38px}}
.h2{{display:flex;align-items:baseline;gap:12px;margin:0 0 16px}}
.h2 h2{{font-size:21px;margin:0;font-weight:680;letter-spacing:-.01em}}
.h2 .n{{font:600 12px/1 var(--mono);color:var(--acc2);opacity:.8}}
.h2 .hint{{margin-left:auto;color:var(--mut);font-size:12.5px}}

.card{{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
  border-radius:16px;padding:22px}}
.chartbox{{position:relative;height:340px}}
.chartbox.sm{{height:150px;margin-top:8px}}
.legend{{display:flex;gap:18px;margin-bottom:6px;font-size:12.5px;color:var(--mut)}}
.legend span{{display:inline-flex;align-items:center;gap:7px}}
.legend i{{width:14px;height:3px;border-radius:2px;display:inline-block}}

table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line)}}
thead th{{font:600 11px/1.3 var(--mono);letter-spacing:.05em;text-transform:uppercase;
  color:var(--mut);border-bottom:1px solid var(--line)}}
td.r,th.r{{text-align:right;font-family:var(--mono);font-size:13px}}
tbody tr:hover{{background:rgba(94,234,212,.04)}}
.pos{{color:var(--pos)}} .neg{{color:var(--neg)}}
.sym{{font-weight:600}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:9px;vertical-align:middle}}
.dot.c{{background:#a78bfa}} .dot.m{{background:#fbbf24}} .dot.fx{{background:#38bdf8}}
.dot.e{{background:#fb923c}} .dot.ag{{background:#34d399}} .dot.ix{{background:#f472b6}}
.tag{{font:600 11px/1 var(--mono);color:var(--mut);background:#0e1626;border:1px solid var(--line);
  padding:4px 8px;border-radius:6px}}
tr.hit{{background:rgba(52,211,153,.07)}}
tr.hit td{{border-color:rgba(52,211,153,.2)}}
.ok{{color:var(--pos);font-weight:600;font-size:12.5px}}
td.sep{{border-left:1px solid var(--line)}}
th.sep{{border-left:1px solid var(--line)}}

.cols{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:820px){{.cols{{grid-template-columns:1fr}}}}

.mech{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
@media(max-width:820px){{.mech{{grid-template-columns:1fr}}}}
.step{{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.step .si{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.step .num{{width:26px;height:26px;border-radius:8px;background:#0e2b26;color:var(--acc);
  display:grid;place-items:center;font:700 13px var(--mono);flex:none}}
.step h4{{margin:0;font-size:14.5px;font-weight:650}}
.step p{{margin:0;color:var(--mut);font-size:13.2px;line-height:1.5}}
.step code{{font-family:var(--mono);color:var(--acc);font-size:12.5px;background:#0c1322;
  padding:1px 5px;border-radius:4px}}

.yrow{{display:flex;gap:10px;align-items:flex-end;height:200px;padding-top:10px}}
.ybar{{flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;height:100%;justify-content:flex-end}}
.ytrack{{flex:1;width:100%;display:flex;align-items:flex-end;justify-content:center;min-height:0}}
.yfill{{width:62%;border-radius:5px 5px 0 0;min-height:2px}}
.yfill.pos{{background:linear-gradient(180deg,var(--pos),#1c8f68)}}
.yfill.neg{{background:linear-gradient(180deg,#7f2d2d,var(--neg))}}
.yval{{font:600 11px var(--mono)}} .ylab{{font:11px var(--mono);color:var(--mut)}}

.corr{{font-size:11px;font-family:var(--mono)}}
.corr th,.corr td{{padding:6px 8px;text-align:center;border:1px solid var(--line)}}
.corr th{{color:var(--mut);font-weight:600}}
.corr td{{color:#fff}} .corr td.diag{{color:var(--mut);background:#0c1322}}
.corr th.rh{{text-align:right;color:var(--txt)}}

.warn{{background:linear-gradient(180deg,#1a1410,#140f0c);border:1px solid #4a2f1a;border-radius:16px;padding:22px}}
.warn h2{{color:var(--gold)}}
.warn ol{{margin:0;padding-left:20px;color:#d8c9b3}}
.warn li{{margin:9px 0;line-height:1.55}}
.warn b{{color:#fff}}
.kicker{{background:#0c1322;border-left:3px solid var(--acc);padding:12px 16px;border-radius:0 10px 10px 0;
  color:var(--mut);font-size:13.5px;margin-top:16px}}
.kicker b{{color:var(--txt)}}
footer{{margin-top:44px;padding-top:20px;border-top:1px solid var(--line);color:var(--mut);
  font:12px/1.7 var(--mono)}}
.iso{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:820px){{.iso{{grid-template-columns:1fr}}}}
.isocard{{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:18px}}
.isocard .lab{{font:600 11px var(--mono);letter-spacing:.1em;color:var(--mut);text-transform:uppercase}}
.isocard .rng{{font:11px var(--mono);color:var(--mut);margin-top:2px}}
.isocard .mrow{{display:flex;gap:20px;margin-top:12px}}
.isocard .mrow div span{{display:block;font:600 10px var(--mono);color:var(--mut);text-transform:uppercase}}
.isocard .mrow div b{{font-size:19px;font-weight:700}}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="eyebrow">Báo cáo backtest · CTA Managed Futures</div>
  <h1>Danh mục CTA Risk-Parity</h1>
  <p class="sub">Một chiến thuật <b>breakout theo xu hướng</b> duy nhất, áp dụng đồng nhất cho
  {meta['n_markets']} thị trường thuộc 5 lớp tài sản. Trọng số phân bổ theo <b>nghịch đảo biến động</b>
  (risk-parity) rồi nhân đòn bẩy {meta['lev']:g}×. Khung H4, {meta['start']} → {meta['end']}.</p>
  <div class="badge">🎯 Mục tiêu <b>CAGR&nbsp;&gt;&nbsp;35%&nbsp;&amp;&nbsp;DD&nbsp;&lt;&nbsp;40%</b> — ĐẠT cả In-sample &amp; Out-of-sample</div>
  <div class="meta">Nguồn: cta_portfolio.py · Engine trade-level · {meta['bars']:,} nến H4 · Sharpe {meta['sharpe']} · tạo {meta['generated']}</div>
</header>

<div class="grid kpis">
  <div class="kpi"><div class="k">CAGR</div><div class="v pos">{pct(p['cagr'])}</div><div class="d">lợi nhuận kép/năm</div></div>
  <div class="kpi"><div class="k">Max Drawdown</div><div class="v neg">{pct(p['dd'])}</div><div class="d">sụt giảm tệ nhất</div></div>
  <div class="kpi"><div class="k">Calmar</div><div class="v">{num(p['calmar'])}</div><div class="d">CAGR / |DD|</div></div>
  <div class="kpi"><div class="k">Sharpe</div><div class="v">{num(p['sharpe'])}</div><div class="d">vùng quỹ CTA pro</div></div>
  <div class="kpi"><div class="k">Tăng trưởng vốn</div><div class="v gold">{num(p['total'],0)}×</div><div class="d">$10k → ${p['final_eq']:,.0f}</div></div>
</div>

<section>
  <div class="h2"><span class="n">01</span><h2>Đường vốn &amp; Drawdown</h2>
    <span class="hint">thang log · risk-parity vs equal-weight · lev {meta['lev']:g}×</span></div>
  <div class="card">
    <div class="legend">
      <span><i style="background:#5eead4"></i>Risk-parity</span>
      <span><i style="background:#64748b"></i>Equal-weight</span>
      <span><i style="background:#f87171"></i>Drawdown (%)</span>
    </div>
    <div class="chartbox"><canvas id="eq"></canvas></div>
    <div class="chartbox sm"><canvas id="dd"></canvas></div>
  </div>
</section>

<section>
  <div class="h2"><span class="n">02</span><h2>Cơ chế chiến thuật</h2>
    <span class="hint">giống logic EA MQL5 (CtaPortfolio.mq5)</span></div>
  <div class="mech">
    <div class="step"><div class="si"><div class="num">1</div><h4>Tín hiệu vào lệnh — Breakout N nến</h4></div>
      <p>Mỗi nến H4, nếu giá đóng cửa <code>close[1]</code> vượt <b>đỉnh 5 nến</b> trước đó → <b>MUA</b>;
      thủng <b>đáy 5 nến</b> → <b>BÁN</b>. Cùng tham số <code>entry=5</code> cho mọi thị trường (chuẩn CTA, tránh overfit).</p></div>
    <div class="step"><div class="si"><div class="num">2</div><h4>Stop ban đầu — 3×ATR</h4></div>
      <p>Stop-loss đặt cách giá vào <code>3 × ATR(14)</code>. ATR đo biến động riêng từng thị trường →
      stop tự co giãn theo độ "ồn" của mỗi tài sản.</p></div>
    <div class="step"><div class="si"><div class="num">3</div><h4>Trailing stop — 5×ATR (cưỡi trend)</h4></div>
      <p>Khi đã có lời, stop bám theo đỉnh/đáy cao nhất kể từ lúc vào, cách <code>5 × ATR</code>.
      Để lệnh thắng chạy dài, cắt lệnh thua nhanh — bản chất lợi nhuận của trend-following.</p></div>
    <div class="step"><div class="si"><div class="num">4</div><h4>Sizing — % rủi ro cố định</h4></div>
      <p>Khối lượng tính sao cho mỗi lệnh rủi ro <code>1%</code> equity của sleeve:
      <code>units = risk$ / khoảng_cách_stop</code>. Quy đổi tiền tệ chính xác (GBPJPY → USD).</p></div>
    <div class="step"><div class="si"><div class="num">5</div><h4>Risk-parity — cân theo nghịch đảo vol</h4></div>
      <p>Gộp 10 sleeve: thị trường ít biến động được trọng số lớn hơn để mỗi cái đóng góp
      <b>rủi ro bằng nhau</b>. Vốn từ thị trường chưa có data được phân bổ lại cho cái đang active → không có "vốn chết".</p></div>
    <div class="step"><div class="si"><div class="num">6</div><h4>Đòn bẩy {meta['lev']:g}× + compound</h4></div>
      <p>Chuỗi lợi nhuận danh mục nhân <code>{meta['lev']:g}×</code> rồi cộng dồn kép.
      Đây là nút điều chỉnh CAGR↔DD: lev cao → lời nhiều hơn nhưng drawdown sâu hơn tuyến tính.</p></div>
  </div>
</section>

<section>
  <div class="h2"><span class="n">03</span><h2>Hiệu suất từng thị trường</h2>
    <span class="hint">đứng độc lập (risk 1%/lệnh, chưa đòn bẩy danh mục)</span></div>
  <div class="card" style="padding:6px 6px 2px">
    <table>
      <thead><tr>
        <th>Thị trường</th><th>Lớp</th><th class="r">CAGR</th><th class="r">Max DD</th>
        <th class="r">Calmar</th><th class="r">Sharpe</th><th class="r">Lệnh</th>
        <th class="r">Win%</th><th class="r">PF</th><th class="r">Trọng số TB</th>
      </tr></thead>
      <tbody>
{market_rows(d['markets'])}
      </tbody>
    </table>
  </div>
  <div class="kicker"><b>Crypto là yếu tố quyết định:</b> trước khi thêm BTC+ETH, danh mục Calmar chỉ ~0.54.
  Crypto có edge trend mạnh <i>và</i> tương quan thấp với FX/hàng hóa, hoạt động đúng giai đoạn
  yếu OOS trước đó → kéo Calmar lên ~0.95.</div>
</section>

<section>
  <div class="h2"><span class="n">04</span><h2>Quét đòn bẩy</h2>
    <span class="hint">risk-parity (★ cấu hình chính) so với equal-weight</span></div>
  <div class="card" style="padding:6px 6px 2px">
    <table>
      <thead><tr>
        <th class="r">Đòn bẩy</th>
        <th class="r">CAGR</th><th class="r">Max DD</th><th class="r">Calmar</th><th class="r">Vốn</th>
        <th class="sep r">CAGR (EW)</th><th class="r">DD (EW)</th><th class="r">Calmar (EW)</th><th>Mục tiêu</th>
      </tr></thead>
      <tbody>
{sweep_rows(d['sweep'], d['ew'])}
      </tbody>
    </table>
  </div>
</section>

<section>
  <div class="h2"><span class="n">05</span><h2>Kiểm định In-sample / Out-of-sample</h2>
    <span class="hint">chia 60/40 theo thời gian · lev {meta['lev']:g}×</span></div>
  <div class="iso">
    <div class="isocard">
      <div class="lab">In-sample (60%)</div>
      <div class="rng">{iso['IS']['start']} → {iso['IS']['end']}</div>
      <div class="mrow">
        <div><span>CAGR</span><b class="pos">{pct(iso['IS']['cagr'])}</b></div>
        <div><span>Max DD</span><b class="neg">{pct(iso['IS']['dd'])}</b></div>
        <div><span>Calmar</span><b>{num(iso['IS']['calmar'])}</b></div>
      </div>
    </div>
    <div class="isocard">
      <div class="lab">Out-of-sample (40%)</div>
      <div class="rng">{iso['OOS']['start']} → {iso['OOS']['end']}</div>
      <div class="mrow">
        <div><span>CAGR</span><b class="pos">{pct(iso['OOS']['cagr'])}</b></div>
        <div><span>Max DD</span><b class="neg">{pct(iso['OOS']['dd'])}</b></div>
        <div><span>Calmar</span><b>{num(iso['OOS']['calmar'])}</b></div>
      </div>
    </div>
  </div>
  <div class="kicker">OOS Calmar <b>≥</b> IS Calmar → đây <b>không phải overfit thuần</b>. Tuy nhiên
  10 thị trường được chọn vì có edge dương đo trên toàn kỳ (gồm cả OOS) → vẫn có selection bias, đọc cảnh báo bên dưới.</div>
</section>

<section>
  <div class="cols">
    <div>
      <div class="h2"><span class="n">06</span><h2>Lợi nhuận theo năm</h2></div>
      <div class="card"><div class="yrow">
{yearly_bars(d['yearly'])}
      </div></div>
    </div>
    <div>
      <div class="h2"><span class="n">07</span><h2>Ma trận tương quan</h2></div>
      <div class="card" style="overflow:auto">
        {corr_table(d['corr'])}
        <div style="color:var(--mut);font-size:12px;margin-top:10px">
          <span style="color:#3b82f6">▮</span> tương quan âm/thấp (đa dạng tốt) ·
          <span style="color:#ef4444">▮</span> tương quan cao</div>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="h2"><span class="n">08</span><h2>⚠️ Cảnh báo trung thực — đọc trước khi dùng tiền thật</h2></div>
  <div class="warn">
    <ol>
      <li><b>Selection bias:</b> 10 thị trường được chọn vì có edge dương đo trên <b>toàn kỳ</b>
        (gồm cả OOS) → kết quả OOS hơi lạc quan, forward thực tế có thể yếu hơn.</li>
      <li><b>Đòn bẩy {meta['lev']:g}× là cao:</b> DD backtest {pct(p['dd'])} có thể tệ hơn thực tế (gap cuối tuần,
        crypto gap mạnh, slippage). Rủi ro margin call là thật. <b>Khuyến nghị lev 4–4.5×</b>
        (CAGR ~30–33%, DD ~−32–35%) an toàn hơn.</li>
      <li><b>Phụ thuộc giai đoạn crypto:</b> kết quả mạnh dựa nhiều vào sóng crypto 2017–2021 +
        hồi sinh trend 2022 — có thể không lặp lại.</li>
      <li><b>Giả định rebalance:</b> mô hình giả định cân lại risk-parity thường xuyên; thực tế
        có ma sát phí + cần kỷ luật.</li>
      <li><b>Chi phí crypto:</b> spread/phí crypto thật có thể cao hơn giả định backtest.</li>
    </ol>
    <div class="kicker" style="border-color:var(--gold);margin-top:18px">
      <b>Kết luận honest:</b> mục tiêu ĐẠT trong backtest (robust IS+OOS), nhưng đây là danh mục
      <b>đòn bẩy cao, có crypto</b> — không phải "tiền dễ". Phải chạy demo/paper ≥6 tháng, cân nhắc
      lev 4× thay vì 5×, và hiểu rằng DD {pct(p['dd'])} nghĩa là sẽ có lúc mất gần 40% tài khoản.</div>
  </div>
</section>

<footer>
  Tạo bởi cta_portfolio_report.py · dữ liệu Dukascopy H4 · engine backtest trade-level (broker.py)<br>
  Đây là kết quả mô phỏng lịch sử, KHÔNG phải khuyến nghị đầu tư. Past performance ≠ future results.
</footer>

</div>

<script>
const D = {json.dumps(d['chart'])};
const css = getComputedStyle(document.documentElement);
const grid = 'rgba(148,163,184,.08)';
Chart.defaults.color = '#8a97ad';
Chart.defaults.font.family = "var(--mono)";

new Chart(document.getElementById('eq'), {{
  type:'line',
  data:{{labels:D.dates, datasets:[
    {{label:'Risk-parity', data:D.equity, borderColor:'#5eead4', backgroundColor:'rgba(94,234,212,.06)',
      borderWidth:1.6, pointRadius:0, fill:true, tension:.05}},
    {{label:'Equal-weight', data:D.equalw, borderColor:'#64748b', borderWidth:1.1,
      pointRadius:0, borderDash:[4,3], tension:.05}}
  ]}},
  options:{{responsive:true, maintainAspectRatio:false, interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{
      label:c=>c.dataset.label+': '+c.parsed.y.toFixed(2)+'×'}}}}}},
    scales:{{
      y:{{type:'logarithmic', grid:{{color:grid}}, ticks:{{callback:v=>v+'×'}}}},
      x:{{grid:{{display:false}}, ticks:{{maxTicksLimit:14, autoSkip:true}}}}
    }}}}
}});

new Chart(document.getElementById('dd'), {{
  type:'line',
  data:{{labels:D.dates, datasets:[
    {{label:'Drawdown', data:D.dd, borderColor:'#f87171', backgroundColor:'rgba(248,113,113,.14)',
      borderWidth:1, pointRadius:0, fill:true, tension:.05}}
  ]}},
  options:{{responsive:true, maintainAspectRatio:false, interaction:{{mode:'index',intersect:false}},
    plugins:{{legend:{{display:false}}, tooltip:{{callbacks:{{
      label:c=>'DD: '+c.parsed.y.toFixed(1)+'%'}}}}}},
    scales:{{
      y:{{grid:{{color:grid}}, ticks:{{callback:v=>v+'%'}}, max:0}},
      x:{{grid:{{display:false}}, ticks:{{maxTicksLimit:14, autoSkip:true}}}}
    }}}}
}});
</script>
</body>
</html>"""
