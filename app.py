"""
Turnierverwaltung – Flask + PyYAML in einer einzigen Datei
Speichert alle Daten in data.yaml (legt sie bei Bedarf an).
Start:  python app.py   (oder via Docker)

© 2025 – feel free to adapt!
"""
import os, uuid, yaml, datetime as dt
import calendar
from pathlib import Path
from flask import (
    Flask, request, redirect, url_for,
    flash, render_template_string, make_response,
    session, abort
)

DATA_FILE = Path("data.yaml")
DATE_FMT  = "%Y-%m-%d"
PAST_KEEP_DAYS = 60  # zwei Monate

app = Flask(__name__)
app.secret_key = "change-me-in-production"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")

# ---------- YAML Persistence ----------
def _load():
    if not DATA_FILE.exists():
        return {"tournaments": []}
    with DATA_FILE.open("r", encoding="utf8") as f:
        return yaml.safe_load(f) or {"tournaments": []}

def _save(data):
    with DATA_FILE.open("w", encoding="utf8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

# ---------- Helper ----------
def _today():
    return dt.date.today()

def _parse(dstr):
    if isinstance(dstr, dt.date):
        return dstr
    return dt.datetime.strptime(dstr, DATE_FMT).date()

def _filter_lists():
    data = _load()
    today = _today()
    border = today - dt.timedelta(days=PAST_KEEP_DAYS)
    upcoming, archive = [], []
    for t in data["tournaments"]:
        s_date = _parse(t["start_date"])
        e_date = _parse(t["end_date"])
        # Build dates list
        t["dates"] = []
        for i in range((e_date - s_date).days + 1):
            d = s_date + dt.timedelta(days=i)
            t["dates"].append({
                "iso": d.isoformat(),
                "fmt": d.strftime("%d.%m.%y")
            })
        # Format start/end
        t["start_fmt"] = s_date.strftime("%d.%m.%y")
        t["end_fmt"]   = e_date.strftime("%d.%m.%y")
        # Sort into upcoming/archive
        if e_date >= border:
            upcoming.append(t)
        else:
            archive.append(t)
        # Sort participants
        t["participants"].sort(key=lambda p: p["name"].lower())
    # Sort tournaments
    upcoming.sort(key=lambda t: _parse(t["start_date"]))
    archive.sort(key=lambda t: _parse(t["start_date"]), reverse=True)
    return upcoming, archive

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def index():
    tournaments, _ = _filter_lists()
    filter_name = request.cookies.get("filter", "")
    if filter_name:
        key = filter_name.lower()
        tournaments = [
            t for t in tournaments
            if (key in t["name"].lower())
            or (t.get("location","") and key in t["location"].lower())
            or any(key in p["name"].lower() for p in t["participants"])
        ]
    return _render_page(tournaments, archive=False, filter_name=filter_name)

@app.route("/archive", methods=["GET"])
def archive():
    _, tournaments = _filter_lists()
    filter_name = request.cookies.get("filter", "")
    if filter_name:
        key = filter_name.lower()
        tournaments = [
            t for t in tournaments
            if (key in t["name"].lower())
            or (t.get("location","") and key in t["location"].lower())
            or any(key in p["name"].lower() for p in t["participants"])
        ]
    return _render_page(tournaments, archive=True, filter_name=filter_name)

@app.route("/create", methods=["POST"])
def create():
    name        = request.form.get("name", "").strip()
    start_date  = request.form.get("start_date", "").strip()
    end_date    = request.form.get("end_date", "").strip() or start_date
    location    = request.form.get("location", "").strip()
    link        = request.form.get("link", "").strip()
    description = request.form.get("description", "").strip()

    if not name or not start_date:
        flash("Bitte Name und Startdatum angeben.")
        return redirect(url_for("index"))

    try:
        sd = _parse(start_date)
        ed = _parse(end_date)
        if ed < sd:
            raise ValueError
    except ValueError:
        flash("Ungültiges Datum. Enddatum muss ≥ Startdatum sein.")
        return redirect(url_for("index"))

    data = _load()
    data["tournaments"].append({
        "id": uuid.uuid4().hex,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "location": location,
        "link": link,
        "description": description,
        "participants": []
    })
    _save(data)
    flash("Turnier angelegt!")
    return redirect(url_for("index"))

@app.route("/signup/<tid>", methods=["POST"])
def signup(tid):
    pname = request.form.get("player", "").strip()
    if not pname:
        flash("Bitte einen Namen eingeben.")
        return redirect(url_for("index"))

    status_map = {
        key.split("_",1)[1]: val
        for key,val in request.form.items()
        if key.startswith("status_")
    }
    data = _load()
    for t in data["tournaments"]:
        if t["id"] == tid:
            for p in t["participants"]:
                if p["name"].lower() == pname.lower():
                    p["statuses"] = status_map
                    break
            else:
                t["participants"].append({
                    "id": uuid.uuid4().hex,
                    "name": pname,
                    "statuses": status_map
                })
            break
    _save(data)
    flash("Teilnahmestatus gespeichert!")
    # Redirect back to referrer (archive or index) and scroll to the tournament card
    ref = request.headers.get("Referer", "")
    base = ref.split('#')[0] if ref else url_for("index")
    return redirect(f"{base}#tournament-{tid}")

# ---------- Admin ----------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("password","") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Falsches Passwort.")
    if not session.get("admin"):
        return render_template_string("""
        <form method="post">
          <label>Admin-Passwort</label>
          <input name="password" type="password">
          <button type="submit">Login</button>
        </form>
        """)
    data = _load()
    return render_template_string("""
    <!doctype html><html lang="de"><head><meta charset="utf-8">
    <title>Admin-Panel</title><style>
      :root{--accent:#c00000;}
      body{font-family:system-ui,sans-serif;padding:1rem;}
      .btn-primary{background:var(--accent);color:#fff;padding:.5rem 1rem;border:none;border-radius:.5rem;}
    </style></head><body>
    <h1>Admin-Panel</h1>
    <p><a href="{{ url_for('index') }}">Zurück</a> | 
       <a href="{{ url_for('admin_logout') }}">Logout</a></p>
    {% for t in data["tournaments"] %}
      <fieldset style="margin:1rem 0;padding:1rem;border:1px solid #ddd;">
        <legend>{{ t.name }}</legend>
        <form method="post" action="{{ url_for('delete_tournament', tid=t.id) }}">
          <button class="btn-primary">Turnier löschen</button>
        </form>
        <h4>Teilnehmer</h4>
        {% for p in t.participants %}
          <form method="post" action="{{ url_for('delete_participant', tid=t.id, pid=p.id) }}" style="display:inline-block;margin:.25rem;">
            {{ p.name }}
            <button class="btn-primary">Löschen</button>
          </form>
        {% endfor %}
      </fieldset>
    {% endfor %}
    </body></html>
    """, data=data)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/admin/delete_tournament/<tid>", methods=["POST"])
def delete_tournament(tid):
    if not session.get("admin"): abort(403)
    data = _load()
    data["tournaments"] = [t for t in data["tournaments"] if t["id"]!=tid]
    _save(data)
    flash("Turnier gelöscht.")
    return redirect(url_for("admin"))


@app.route("/admin/delete_participant/<tid>/<pid>", methods=["POST"])
def delete_participant(tid, pid):
    if not session.get("admin"): abort(403)
    data = _load()
    for t in data["tournaments"]:
        if t["id"] == tid:
            t["participants"] = [p for p in t["participants"] if p["id"]!=pid]
    _save(data)
    flash("Teilnehmer gelöscht.")
    return redirect(url_for("admin"))

# ---------- Tournament Edit ----------
@app.route("/edit_tournament/<tid>", methods=["POST"])
def edit_tournament(tid):
    link = request.form.get("link", "").strip()
    description = request.form.get("description", "").strip()
    data = _load()
    for t in data["tournaments"]:
        if t["id"] == tid:
            t["link"] = link
            t["description"] = description
            break
    _save(data)
    flash("Turnier aktualisiert!")
    ref = request.headers.get("Referer", "")
    base = ref.split('#')[0] if ref else url_for("index")
    return redirect(f"{base}#tournament-{tid}")

@app.route("/set_filter", methods=["POST"])
def set_filter():
    resp = make_response(redirect(request.headers.get("Referer", url_for("index"))))
    # If clear button was clicked
    if request.form.get("clear"):
        resp.delete_cookie("filter")
        return resp
    # Otherwise set or delete based on filter input
    filter_name = request.form.get("filter", "").strip()
    if filter_name:
        resp.set_cookie("filter", filter_name, max_age=365*24*3600)
    else:
        resp.delete_cookie("filter")
    return resp

# ---------- Template ----------
def _render_page(tournaments, archive=False, filter_name=""):
    base_tpl = """
    <!doctype html><html lang="de"><head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Turnierverwaltung</title>
    
    <style>
    :root{--accent:#c00000;}
    body{font-family:system-ui,sans-serif;margin:0;padding:1rem;background:#fafafa;}
    header, .card{background:#fff;border-radius:.75rem;}
    header{display:flex;align-items:center;padding:1rem;margin-bottom:1rem;box-shadow:0 2px 4px rgba(0,0,0,.1);}
    .logo{max-width:90px;height:auto;}
    .headline{color:var(--accent);font-size:1.75rem;font-weight:600;margin-left:1rem;}
    .tabs{display:flex;gap:1rem;margin:1rem 0;}
    .tabs a{padding:.5rem 1rem;text-decoration:none;border-radius:.5rem;color:#333;background:#f0f0f0;}
    .tabs a.active, .tabs a:hover{background:var(--accent);color:#fff;}
    .btn-primary{background:var(--accent);color:#fff;padding:.5rem 1rem;border:none;border-radius:.5rem;}
    .form-label{margin-top:1rem;display:block;font-weight:500;}
    input, select, textarea{width:100%;padding:.5rem;border:1px solid #ddd;border-radius:.5rem;margin-top:.25rem;}
    .grid{display:flex;flex-direction:column;gap:1.5rem;}
    .status-table{width:100%;border-collapse:collapse;margin:1rem 0;overflow-x:auto;}
    .status-table th, .status-table td{border:1px solid #ddd;padding:.75rem;text-align:center;white-space:nowrap;}
    .status-attending{background:#d4edda;} .status-interested{background:#fff3cd;} .status-no{background:#f8d7da;}
    .status-field{display:flex;align-items:center;gap:.5rem;margin-bottom:.75rem;}
    .status-field label{width:5rem;}
    .card form .form-group input,
    .card form .status-field select{width:auto;max-width:200px;}
        /* Card layout */
        .card { padding: 1.5rem; margin-bottom: 1.5rem; border: 1px solid #e0e0e0; box-shadow:0 2px 4px rgba(0,0,0,.05);}
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .card-header h2 { margin: 0; font-size: 1.5rem; }
        .card-header small { color: #666; }
        .card-body { display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; }
        .card-left { overflow-x: auto; }
        .card-right { background: #f9f9f9; padding: 1rem; border-radius: 0.5rem; }
        .status-table th { background: var(--accent); color: #fff; }
        /* Always show details if present */
        .detail-container { margin-bottom: 1rem; }
        /* Create form toggle */
        .create-container { display: none; margin-top: 0.5rem; }
        .create-container.active { display: block; }
    /* ---------- Mobile Tweaks ---------- */
    /* Header scales on narrow screens */
    header { flex-wrap: wrap; }
    .logo   { max-width: 14vw; height: auto; }
    .headline {
      font-size: clamp(1.25rem, 4vw, 1.75rem);
      margin-top: .5rem;
    }

    /* Stack table + form vertically on small screens */
    @media (max-width: 600px) {
      .card-body  { display: flex; flex-direction: column; }
      .card-right { margin-top: 1rem; }
      .card-left table { width: 100%; }
    }
    /* Calendar responsive: mobile swipe, desktop fixed 4 months */
    .cal-wrapper {
      display: flex;
      gap: 1rem;
      -webkit-overflow-scrolling: touch;
      scroll-snap-type: x mandatory;
      padding-bottom: .5rem;
    }
    @media (max-width: 900px) {
      .cal-wrapper { overflow-x: auto; }
      .cal { flex: 0 0 260px; scroll-snap-align: start; }
    }
    @media (min-width: 901px) {
      .cal-wrapper { overflow: hidden; }
      .cal { flex: 0 0 25%; /* four per row */ }
    }
    /* Calendar cell styling remains unchanged */
    .cal { border:1px solid #ddd; border-radius:.5rem; overflow:hidden; }
    .cal-header { background:var(--accent); color:#fff; text-align:center; padding:.25rem 0; font-weight:600; }
    .cal-grid { display:grid; grid-template-columns:repeat(7,1fr); }
    .cal-cell { padding:.25rem; text-align:center; border-bottom:1px solid #eee; border-right:1px solid #eee; }
    .cal-cell:last-child { border-right:none; }
    .cal-day { font-size:.85rem; color:#666; }
    .cal-cell.active { background:#d4edda; cursor:pointer; }
    .cal-cell.active:hover { background:#bfe0c2; }
    /* Standard links in accent red, no underline */
    a, a:hover {
      color: var(--accent);
      text-decoration: none;
    }
        /* Tournament edit form toggle */
        .edit-tour-container { display: none; margin-top: 1rem; }
        .edit-tour-container.active { display: block; }
    </style>
    </head><body>
    <header>
      <img src="https://beta.aixtraball.de/static/images/logo.png" class="logo" alt="Logo">
      <h1 class="headline">Turnierverwaltung</h1>
    </header>
    <nav class="tabs">
      <a href="{{ url_for('index') }}" class="{% if not archive %}active{% endif %}">Übersicht</a>
      <a href="{{ url_for('archive') }}" class="{% if archive %}active{% endif %}">Archiv</a>
    </nav>
    <form method="post" action="{{ url_for('set_filter') }}" style="margin-bottom:1rem;">
  <input type="text" name="filter" placeholder="Nach Teilnehmer, Event oder Location filtern"
         value="{{ filter_name }}"
         style="padding:.5rem;border:1px solid #ddd;border-radius:.5rem;width:200px;">
  <button class="btn-primary" type="submit">Anwenden</button>
  {% if filter_name %}
    <button class="btn-primary" type="submit" name="clear" value="1">Löschen</button>
  {% endif %}
</form>
    <div class="cal-wrapper">
      {% for m in calendar_months %}
      <div class="cal">
        <div class="cal-header">{{ m.name }}</div>
        <div class="cal-grid">
          {% for day in ['Mo','Tu','We','Th','Fr','Sa','Su'] %}
            <div class="cal-cell cal-day">{{ day }}</div>
          {% endfor %}
          {% for wk in m.weeks %}
            {% for c in wk %}
              {% if c.day %}
                {% if c.active %}
                  <a href="#tournament-{{ c.tid }}" class="cal-cell active">{{ c.day }}</a>
                {% else %}
                  <div class="cal-cell">{{ c.day }}</div>
                {% endif %}
              {% else %}
                <div class="cal-cell">&nbsp;</div>
              {% endif %}
            {% endfor %}
          {% endfor %}
        </div>
      </div>
      {% endfor %}
    </div>
    <datalist id="player_names">
      {% for name in all_names %}<option value="{{ name }}">{% endfor %}
    </datalist>

    {% if not archive %}
    <div class="card">
      <button type="button" class="btn-primary create-toggle">Neues Turnier anlegen</button>
      <div class="create-container">
        <h2>Neues Turnier anlegen</h2>
        <form method="post" action="{{ url_for('create') }}">
          <label class="form-label">Name</label>
          <input name="name" placeholder="Turniername" required>
          <label class="form-label">Startdatum</label>
          <input type="date" name="start_date" required>
          <label class="form-label">Enddatum <small>(optional)</small></label>
          <input type="date" name="end_date">
          <label class="form-label">Ort <small>(optional)</small></label>
          <input name="location" placeholder="Ort">
          <label class="form-label">Link <small>(optional)</small></label>
          <input name="link" placeholder="https://example.com">
          <label class="form-label">Beschreibung <small>(optional)</small></label>
          <textarea name="description" rows="3"></textarea>
          <button class="btn-primary" type="submit">Speichern</button>
        </form>
      </div>
    </div>
    {% endif %}

    <div class="grid">
    {% for t in tournaments %}
      <div class="card" id="tournament-{{ t.id }}">
        <div class="card-header">
          <div>
            <h2>{{ t.name }}</h2>
            <small>
              {{ t.start_fmt }}{% if t.end_date and t.end_date!=t.start_date %} – {{ t.end_fmt }}{% endif %}
              {% if t.location %} · {{ t.location }}{% endif %}
            </small>
          </div>
          <svg class="edit-tour-toggle" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="var(--accent)" viewBox="0 0 24 24" style="cursor:pointer;">
            <path d="M3 17.25V21h3.75l11.06-11.06-3.75-3.75L3 17.25zm2.16 1.34l.59-2.36 2.36.59-2.95 1.77zm13.7-10.7l-1.77 1.77-3.75-3.75 1.77-1.77a.996.996 0 011.41 0l2.34 2.34a.996.996 0 010 1.41z"/>
          </svg>
        </div>
        <div class="detail-container">
          {% if t.link %}
            <small><a href="{{ t.link }}" target="_blank">{{ t.link }}</a></small>
          {% endif %}
          {% if t.description %}
            <small style="white-space: pre-wrap; display: block;">{{ t.description }}</small>
          {% endif %}
        </div>
        <div class="edit-tour-container">
          <form method="post" action="{{ url_for('edit_tournament', tid=t.id) }}">
            <label class="form-label">Link</label>
            <input name="link" value="{{ t.link or '' }}">
            <label class="form-label">Beschreibung</label>
            <textarea name="description" rows="2">{{ t.description or '' }}</textarea>
            <button class="btn-primary" type="submit">Speichern</button>
          </form>
        </div>
        <div class="card-body">
          <div class="card-left">
            <table class="status-table">
              <thead><tr><th>Teilnehmer</th>{% for d in t.dates %}<th>{{ d.fmt }}</th>{% endfor %}<th>Aktion</th></tr></thead>
              <tbody>
                {% for p in t.participants %}
                <tr>
                  <td>{{ p.name }}</td>
                  {% for d in t.dates %}
                    {% set stat = p.statuses.get(d.iso,'no') %}
                    <td class="status-{{ stat }}">{% if stat=='attending' %}✓{% elif stat=='interested' %}?{% else %}×{% endif %}</td>
                  {% endfor %}
                  <td>
                    <svg class="edit-btn" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="var(--accent)" viewBox="0 0 24 24" style="cursor:pointer;"
                       title="Bearbeiten"
                       data-name="{{ p.name }}"
                       data-statuses='{{ p.statuses|tojson }}'>
                      <path d="M3 17.25V21h3.75l11.06-11.06-3.75-3.75L3 17.25zm2.16 1.34l.59-2.36 2.36.59-2.95 1.77zm13.7-10.7l-1.77 1.77-3.75-3.75 1.77-1.77a.996.996 0 011.41 0l2.34 2.34a.996.996 0 010 1.41z"/>
                    </svg>
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          <div class="card-right">
            <form method="post" action="{{ url_for('signup', tid=t.id) }}">
              <div class="form-group">
                <input type="text" name="player" list="player_names" placeholder="Max Mustermann" required>
              </div>
              {% for d in t.dates %}
              <div class="status-field">
                <label class="form-label" for="select_{{ d.iso }}">{{ d.fmt }}</label>
                <select name="status_{{ d.iso }}" id="select_{{ d.iso }}">
                  <option value="attending">Angemeldet</option>
                  <option value="interested">Interesse</option>
                  <option value="no">keine Teilnahme</option>
                </select>
              </div>
              {% endfor %}
              <button class="btn-primary" type="submit">Absenden</button>
            </form>
          </div>
        </div>
      </div>
    {% endfor %}
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', () => {
      document.body.addEventListener('click', e => {
        // Toggle tournament edit form
        if (e.target.classList.contains('edit-tour-toggle')) {
          const btn = e.target;
          const card = btn.closest('.card');
          const container = card.querySelector('.edit-tour-container');
          if (container) container.classList.toggle('active');
          return;
        }
        // Create toggle
        if (e.target.classList.contains('create-toggle')) {
          e.target.nextElementSibling.classList.toggle('active');
          return;
        }
        // Edit participant: prefill signup form
        const pbtn = e.target.closest('.edit-btn');
        if (pbtn) {
          const btn = pbtn;
          const card = btn.closest('.card');
          const form = card.querySelector('form[action*="signup"]');
          const statuses = JSON.parse(btn.getAttribute('data-statuses'));
          // Prefill name
          form.querySelector('input[name="player"]').value = btn.getAttribute('data-name');
          // Prefill statuses
          Object.entries(statuses).forEach(([date, stat]) => {
            const sel = form.querySelector('select[name="status_' + date + '"]');
            if (sel) sel.value = stat;
          });
          form.scrollIntoView({ behavior: 'smooth' });
          return;
        }
      });
    });
    </script>
    </body></html>
    """
    # ----- Build calendar: start with first upcoming tournament month, show 4 months -----
    today = _today()
    # Determine the first month to display (first month with an upcoming or ongoing tournament)
    if tournaments:
        next_start = min(
            _parse(t["start_date"])
            for t in tournaments
            if _parse(t["end_date"]) >= today
        )
        first_month_date = next_start.replace(day=1)
    else:
        first_month_date = today.replace(day=1)
    months = []
    for m_offset in range(4):  # show exactly 4 months on desktop
        month_date = (first_month_date + dt.timedelta(days=32 * m_offset)).replace(day=1)
        year, month = month_date.year, month_date.month
        month_name = month_date.strftime("%B %Y")
        cal = calendar.Calendar(firstweekday=0)
        weeks = []
        for week in cal.monthdatescalendar(year, month):
            week_cells = []
            for d in week:
                iso = d.isoformat()
                has_t = next((t for t in tournaments if iso >= t['start_date'] and iso <= t['end_date']), None)
                week_cells.append({
                    "day": d.day if d.month == month else "",
                    "iso": iso,
                    "active": bool(has_t),
                    "tid": has_t["id"] if has_t else ""
                })
            weeks.append(week_cells)
        months.append({"name": month_name, "weeks": weeks})
    all_names = sorted({p['name'] for t in _load()['tournaments'] for p in t['participants']})
    return render_template_string(base_tpl,
                                  tournaments=tournaments,
                                  archive=archive,
                                  filter_name=filter_name,
                                  all_names=all_names,
                                  calendar_months=months)

if __name__ == "__main__":
    print("📣 Starte Turnierverwaltung auf http://127.0.0.1:8002")
    app.run(debug=True, host="0.0.0.0", port=8002)