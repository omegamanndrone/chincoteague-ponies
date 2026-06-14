"""Curator review console (IMPLEMENTATION_PLAN.md §6) — localhost Flask app.

Build-time tool ONLY; never ships in the app. Click through the changeset
(produced by make_changeset.py) Accept/Reject per item, then Merge accepted items
into the authoring DB (merge.py). Photo items show original <-> crop side-by-side.

Decisions persist to out/review_state.json (layered on each item's default action),
so you can stop and resume. Run:

    .venv/Scripts/python console.py        # http://127.0.0.1:5000
"""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, jsonify, render_template_string, request, send_from_directory

import merge as merge_mod

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
STATE = OUT / "review_state.json"
# All known types across both sources (ingest backup + website scrape). The header
# and dashboard show only those PRESENT in the loaded changeset, so one console
# serves either review session.
ALL_TYPES = ("photo", "region", "band", "note", "field_change", "new_horse", "departed")
ACTION_BY_TYPE = {  # buttons offered per type
    "photo": ["accept", "reject"],
    "region": ["accept", "reject"],
    "band": ["accept", "reject"],
    "note": ["skip"],  # local-only, not canon
    "field_change": ["accept", "reject"],  # accept = take website; reject = keep book
    "new_horse": ["accept", "reject"],     # accept = add pony;     reject = skip it
    "departed": ["accept", "reject"],      # accept = delete pony;  reject = keep it
}

app = Flask(__name__)


def load_changeset() -> dict:
    return json.loads((OUT / "changeset.json").read_text(encoding="utf-8"))


def present_types(cs: dict) -> list[str]:
    """Types actually present in this changeset, in canonical order."""
    have = {it["type"] for it in cs["items"]}
    return [t for t in ALL_TYPES if t in have]


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def effective(item: dict, state: dict) -> str:
    return state.get(item["id"], item["default_action"])


BASE = """
<!doctype html><html><head><meta charset=utf-8><title>Curator — {{title}}</title>
<style>
 body{font:15px/1.5 system-ui,Segoe UI,sans-serif;margin:0;background:#f4f5f7;color:#1b1f24}
 header{background:#1b3a2b;color:#fff;padding:12px 22px;display:flex;gap:18px;align-items:center}
 header b{font-size:17px} header a{color:#bfe3cc;text-decoration:none;font-weight:600}
 header a.active{color:#fff;border-bottom:2px solid #fff}
 main{padding:22px;max-width:1180px;margin:0 auto}
 .pill{display:inline-block;padding:2px 9px;border-radius:11px;font-size:12px;font-weight:700}
 .acc{background:#d7f0dd;color:#1b6b32}.rej{background:#f6d9d9;color:#9a2222}
 .skip{background:#e6e8eb;color:#555}.rev{background:#fde7c2;color:#92600a}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}
 .card{background:#fff;border:1px solid #e2e5e9;border-radius:10px;padding:12px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
 .card.review{border-color:#e8b54e;background:#fffdf6}
 .pair{display:flex;gap:6px} .pair figure{margin:0;flex:1;text-align:center}
 .pair img{width:100%;height:170px;object-fit:contain;background:#222;border-radius:6px}
 .pair figcaption{font-size:11px;color:#777;margin-top:3px}
 .btns{margin-top:10px;display:flex;gap:8px}
 button.b{flex:1;padding:7px;border:1px solid #cfd4da;background:#fff;border-radius:7px;cursor:pointer;font-weight:600;font-size:13px}
 button.b.on-accept{background:#1b6b32;color:#fff;border-color:#1b6b32}
 button.b.on-reject{background:#9a2222;color:#fff;border-color:#9a2222}
 button.b.on-skip{background:#555;color:#fff;border-color:#555}
 .bulkbar{margin:0 0 14px;display:flex;gap:8px;align-items:center;font-size:13px;color:#555}
 button.b2{padding:6px 14px;border:1px solid #cfd4da;background:#fff;border-radius:7px;cursor:pointer;font-weight:600;font-size:13px}
 button.b2.acc:hover{background:#1b6b32;color:#fff;border-color:#1b6b32}
 button.b2.rej:hover{background:#9a2222;color:#fff;border-color:#9a2222}
 table{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden}
 td,th{padding:8px 11px;border-bottom:1px solid #eef0f2;text-align:left;font-size:14px}
 th{background:#eef2ef} tr.stale td{color:#9a2222}
 .meta{font-size:13px;color:#555} .name{font-weight:700}
 .dash a.box{display:block;background:#fff;border:1px solid #e2e5e9;border-radius:10px;padding:16px;text-decoration:none;color:inherit}
 .dash{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-bottom:20px}
 .big{font-size:30px;font-weight:800;color:#1b3a2b} .warn{background:#fff7e6;border:1px solid #f0d28a;padding:10px 14px;border-radius:8px;margin:14px 0;font-size:13px}
 .mergebar{margin-top:8px;display:flex;gap:12px;align-items:center}
 #merge{background:#1b6b32;color:#fff;border:0;padding:11px 20px;border-radius:8px;font-weight:700;cursor:pointer;font-size:15px}
 #mergeout{font-size:13px;color:#1b6b32;font-weight:600}
</style></head><body>
<header><b>🐴 Curator</b>
 <a href="/" class="{{'active' if active=='home' else ''}}">Dashboard</a>
 {% for t in types %}<a href="/review/{{t}}" class="{{'active' if active==t else ''}}">{{ t.replace('_',' ')|title }}{{ '' if t.endswith('ed') else 's' }}</a>{% endfor %}
</header><main>{{ body|safe }}</main>
<script>
function decide(id,action,el){
 fetch('/decide',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({id:id,action:action})}).then(r=>r.json()).then(_=>{
   const card=el.closest('[data-item]');
   card.querySelectorAll('button.b').forEach(b=>b.className='b');
   el.classList.add('on-'+action);
 });
}
function decideAll(type,action){
 if(!confirm('Set ALL '+type+' items to '+action.toUpperCase()+'? (you can still flip individual ones after)'))return;
 fetch('/decide_bulk',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({type:type,action:action})}).then(r=>r.json()).then(_=>location.reload());
}
function doMerge(){
 if(!confirm('Merge all ACCEPTED items into the authoring DB? (additive, idempotent)'))return;
 document.getElementById('mergeout').textContent='merging…';
 fetch('/merge',{method:'POST'}).then(r=>r.json()).then(d=>{
  // generic: show every numeric key the merge report returns (ingest or scrape)
  const parts=Object.keys(d).filter(k=>typeof d[k]==='number').map(k=>k+' '+d[k]);
  document.getElementById('mergeout').textContent='merged → '+parts.join(', ');
 });
}
</script></body></html>
"""


def page(title, active, body, types=None):
    if types is None:
        types = present_types(load_changeset())
    return render_template_string(BASE, title=title, active=active, body=body, types=types)


@app.route("/")
def home():
    cs = load_changeset()
    state = load_state()
    types = present_types(cs)
    is_scrape = cs.get("source") == "scrape"
    by_type = {t: {"total": 0, "accept": 0, "reject": 0, "skip": 0, "review": 0, "decided": 0} for t in types}
    for it in cs["items"]:
        d = by_type[it["type"]]
        d["total"] += 1
        act = effective(it, state)
        d[act] = d.get(act, 0) + 1
        if it["id"] in state:
            d["decided"] += 1
    warn_html = ""
    if cs.get("warnings"):
        lis = "".join(f"<li>{w}</li>" for w in cs["warnings"])
        warn_html = f'<div class=warn><b>{len(cs["warnings"])} warning(s):</b><ul>{lis}</ul></div>'
    # scrape header carries the roster arithmetic so it's obvious what will change
    if is_scrape:
        rs = cs.get("roster_summary", {})
        warn_html = (f'<div class=warn>Website re-scrape → <b>{rs.get("current_total")}</b> current ponies: '
                     f'{rs.get("overlap")} existing + <b>{rs.get("new")} new</b> '
                     f'({rs.get("new_va")} VA, {rs.get("new_md")} MD), '
                     f'<b>{rs.get("departed")} departed</b> (removed). '
                     f'Website values are canonical; book-only fields are preserved (don\'t-clobber).</div>'
                     + warn_html)
    sub_label = {"note": lambda d: f'local-only {d["skip"]}',
                 "departed": lambda d: f'delete {d["accept"]} · keep {d["reject"]}',
                 "field_change": lambda d: f'website {d["accept"]} · keep book {d["reject"]}',
                 "new_horse": lambda d: f'add {d["accept"]} · skip {d["reject"]}'}
    boxes = ""
    for t in types:
        d = by_type[t]
        sub = sub_label.get(t, lambda d: f'accept {d["accept"]} · reject {d["reject"]}')(d)
        label = t.replace("_", " ").title() + ("s" if not t.endswith("ed") else "")
        boxes += (f'<a class=box href="/review/{t}"><div class=big>{d["total"]}</div>'
                  f'<div class=name>{label}</div>'
                  f'<div class=meta>{sub}<br>reviewed {d["decided"]}/{d["total"]}</div></a>')
    heading = ("Website re-scrape review" if is_scrape
               else f'Ingest review — {cs.get("source_file","")}')
    footer = ('<p class=meta>Website is canonical for conflicts; reject a field_change to keep the '
              'book value. Departed ponies with no attached data default to <b>delete</b>.</p>'
              if is_scrape else
              '<p class=meta>Notes are local-only and never merged to canon. '
              'Stale bands default to <b>reject</b>; everything else defaults to <b>accept</b>.</p>')
    body = (f'<h2>{heading}</h2>'
            f'{warn_html}<div class=dash>{boxes}</div>'
            f'<div class=mergebar><button id=merge onclick=doMerge()>Merge accepted → authoring DB</button>'
            f'<span id=mergeout></span></div>{footer}')
    return page("Dashboard", "home", body, types)


@app.route("/review/<t>")
def review(t):
    if t not in ALL_TYPES:
        return "unknown type", 404
    cs = load_changeset()
    state = load_state()
    items = [it for it in cs["items"] if it["type"] == t]
    label = t.replace("_", " ").title()
    body = f'<h2>{label}s <span class=meta>({len(items)})</span></h2>'
    if t != "note":
        accept_lbl = {"departed": "Delete all", "field_change": "Take website (all)"}.get(t, "Accept all")
        reject_lbl = {"departed": "Keep all", "field_change": "Keep book (all)", "new_horse": "Skip all"}.get(t, "Reject all")
        body += (f'<div class=bulkbar>Bulk: '
                 f'<button class="b2 acc" onclick="decideAll(\'{t}\',\'accept\')">{accept_lbl}</button>'
                 f'<button class="b2 rej" onclick="decideAll(\'{t}\',\'reject\')">{reject_lbl}</button>'
                 f'<span>— or decide each below</span></div>')
    if t == "new_horse":
        body += '<div class=grid>'
        for it in items:
            act = effective(it, state)
            mk = ", ".join(it.get("markings") or []) or "—"
            body += (
                f'<div class=card data-item="{it["id"]}">'
                f'<div class=name>{it["name"]} '
                f'<span class="pill acc">{it["state"]}</span></div>'
                f'<div class=meta>ped {it["pedigree_id"]} · {it.get("sex","")} · '
                f'{it.get("color","")} · age {it.get("age","?")}</div>'
                f'<div class=meta style="margin:6px 0"><b>markings:</b> {mk}</div>'
                f'{_btns(it, act)}</div>')
        body += '</div>'
    elif t == "departed":
        rows = ""
        for it in items:
            act = effective(it, state)
            c = it.get("canon", {})
            tag = ('<span class="pill acc">clean</span>' if it.get("clean")
                   else f'<span class="pill rev">has data: {c}</span>')
            rows += (f'<tr class="{"" if it.get("clean") else "stale"}">'
                     f'<td class=name>{it["name"]}</td><td>ped {it["pedigree_id"]}</td>'
                     f'<td>{tag}</td><td>{_btns(it, act, inline=True)}</td></tr>')
        body += ('<p class=meta>Off both Current rosters → propose <b>delete</b>. '
                 'Any with attached canon data are flagged for a human (default review).</p>'
                 f'<table><tr><th>Horse</th><th>Pedigree</th><th>Canon data</th><th>Decision</th></tr>{rows}</table>')
    elif t == "field_change":
        rows = ""
        for it in items:
            act = effective(it, state)
            rows += (f'<tr><td class=name>{it["name"]}</td><td>{it["field"]}</td>'
                     f'<td>{it.get("book_value")!r}</td><td><b>{it.get("scrape_value")!r}</b></td>'
                     f'<td>{_btns(it, act, inline=True)}</td></tr>')
        body += ('<p class=meta>Website value is canonical (more precise/correct). '
                 '<b>Accept</b> takes the website value; <b>Reject</b> keeps the book value.</p>'
                 f'<table><tr><th>Horse</th><th>Field</th><th>Book</th><th>Website</th><th>Decision</th></tr>{rows}</table>')
    elif t == "photo":
        body += '<div class=grid>'
        for it in items:
            act = effective(it, state)
            review_cls = " review" if not it["horse_detected"] else ""
            conf = f'conf {it["detection_conf"]}' if it["horse_detected"] else '<span class="pill rev">NO HORSE — review</span>'
            crop = it.get("cropped_path")
            crop_img = (f'<img src="/img/cropped/{Path(crop).name}">' if crop else '<img>')
            body += (
                f'<div class=card{review_cls} data-item="{it["id"]}">'
                f'<div class=name>{it["name"]} <span class=meta>· ped {it["pedigree_id"]}</span></div>'
                f'<div class=meta>{conf}</div>'
                f'<div class=pair>'
                f'<figure><img src="/img/original/{Path(it["original_path"]).name}"><figcaption>original</figcaption></figure>'
                f'<figure>{crop_img}<figcaption>crop + © K. Kent</figcaption></figure>'
                f'</div>{_btns(it, act)}</div>')
        body += '</div>'
    elif t == "note":
        body += '<p class=meta>Personal notes — <b>never merged to canon</b>. Shown for the departed-gate / cutover remap.</p><div class=grid>'
        for it in items:
            body += (f'<div class=card data-item="{it["id"]}"><div class=name>{it["name"]} '
                     f'<span class=meta>· ped {it["pedigree_id"]}</span></div>'
                     f'<div class=meta style="margin:6px 0">{it["note"]}</div>{_btns(it, effective(it, state))}</div>')
        body += '</div>'
    else:  # region / band as a table
        rows = ""
        for it in items:
            act = effective(it, state)
            if t == "region":
                cells = f'<td class=name>{it["name"]}</td><td>{it["region"]}</td><td>{it["observed"]}</td>'
            else:
                stale = "" if it["is_current"] else "older"
                tag = ('<span class="pill acc">current</span>' if it["is_current"]
                       else '<span class="pill skip">older sighting</span>')
                cells = (f'<td class=name>{it["mare_name"]}</td><td>→ {it["stallion_name"]}</td>'
                         f'<td>{it["date_recorded"]} {tag}</td>')
                cells = f'<tr class="{stale}">' + cells
            row_open = "" if t == "band" else "<tr>"
            rows += f'{row_open if t=="region" else ""}{cells}<td>{_btns(it, act, inline=True)}</td></tr>'
        head = ('<th>Horse</th><th>Region</th><th>Observed</th><th>Decision</th>' if t == "region"
                else '<th>Mare</th><th>Stallion</th><th>Date</th><th>Decision</th>')
        body += f'<table><tr>{head}</tr>{rows}</table>'
    return page(label, t, body)


def _btns(it, act, inline=False):
    actions = ACTION_BY_TYPE[it["type"]]
    bs = ""
    for a in actions:
        on = f" on-{a}" if act == a else ""
        bs += f'<button class="b{on}" onclick="decide(\'{it["id"]}\',\'{a}\',this)">{a.capitalize()}</button>'
    wrap = "" if inline else "btns"
    span = "" if inline else ""
    return f'<div class="{wrap}" {"data-item="+chr(34)+it["id"]+chr(34) if inline else ""}>{bs}</div>'


@app.route("/decide", methods=["POST"])
def decide():
    data = request.get_json(force=True)
    state = load_state()
    state[data["id"]] = data["action"]
    save_state(state)
    return jsonify(ok=True, id=data["id"], action=data["action"])


@app.route("/decide_bulk", methods=["POST"])
def decide_bulk():
    data = request.get_json(force=True)
    t, action = data["type"], data["action"]
    cs = load_changeset()
    state = load_state()
    n = 0
    for it in cs["items"]:
        if it["type"] == t:
            state[it["id"]] = action
            n += 1
    save_state(state)
    return jsonify(ok=True, count=n)


@app.route("/img/<kind>/<path:filename>")
def img(kind, filename):
    folder = {"original": OUT / "photos_original", "cropped": OUT / "photos_cropped"}.get(kind)
    if folder is None:
        return "bad kind", 404
    # Review crops get re-generated in place (e.g. watermark tweaks) under the
    # SAME filename, so tell the browser never to cache them — otherwise a
    # re-crop appears to "do nothing" until a hard refresh.
    resp = send_from_directory(folder, filename)
    resp.headers["Cache-Control"] = "no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.route("/merge", methods=["POST"])
def do_merge():
    report = merge_mod.merge(OUT, merge_mod.DEFAULT_DB, load_state())
    return jsonify(report)


def _open():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    if not (OUT / "changeset.json").exists():
        raise SystemExit("no changeset.json — run make_changeset.py first")
    Timer(1.0, _open).start()
    app.run(debug=False, port=5000)
