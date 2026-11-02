#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chalaane ke liye :  python sap.py
Logo         :  logo.ico aur/ya logo.png isi folder mein rakhein.
Data         :  sap.db  (SQLite, isi folder mein apne-aap banti hai)
"""
from __future__ import annotations

import os
import io
import sys
import re
import glob
import gc
import sqlite3
import ctypes
import traceback
import csv
import json
import math
import time
import base64
import secrets
import calendar
import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
import tempfile
import webbrowser
import tkinter as tk
from pathlib import Path
from typing import Any
from tkinter import ttk, filedialog, messagebox
from html import escape

# --------------------------------------------------------------------------- paths
IS_COMPILED = bool(getattr(sys, "frozen", False)) or ("__compiled__" in globals())
if IS_COMPILED:
    BASE = os.path.dirname(os.path.abspath(sys.argv[0] or sys.executable))
    RES = getattr(sys, "_MEIPASS", BASE)
else:
    BASE = RES = os.path.dirname(os.path.abspath(__file__))

def _data_dir():
    env = os.environ.get("SAP_DATA_DIR")
    if env:
        return os.path.abspath(os.path.expandvars(env))
    if not IS_COMPILED:
        return BASE
    try:
        with open(os.path.join(BASE, "sap_data_dir.txt"), encoding="utf-8-sig") as f:
            p = f.readline().strip()
        if p:
            return os.path.abspath(os.path.expandvars(p))
    except OSError:
        pass
    if os.path.exists(os.path.join(BASE, "sap.db")):
        return BASE
    return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "SmartAccountPro")

DATA = _data_dir()
try:
    os.makedirs(DATA, exist_ok=True)
except OSError:
    pass
DB_FILE = os.environ.get("FEEBOOK_SAP_DB_FILE", os.path.join(DATA, "sap.db"))
OLD_JSON = next((p for p in (os.path.join(DATA, "smart_account_data.json"), os.path.join(BASE, "smart_account_data.json"))
                 if os.path.exists(p)), os.path.join(DATA, "smart_account_data.json"))
K = 1.0

def find_logo(name):
    for d in (BASE, RES):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None

LOGO_ICO = find_logo("logo.ico")
LOGO_PNG = find_logo("logo.png")
_img_cache = {}
_uri_cache = {}

try:
    from PIL import Image, ImageTk
    RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
except Exception:
    Image = ImageTk = None
    RESAMPLE = None

def log_error(text):
    try:
        p = os.path.join(DATA, "sap_error.log")
        if os.path.exists(p) and os.path.getsize(p) > 512 * 1024:
            os.remove(p)
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n{text}\n")
    except OSError:
        pass

def load_logo_image(size=None):
    key = size or 0
    if key in _img_cache:
        return _img_cache[key]
    path = LOGO_PNG or LOGO_ICO
    ph = None
    if path:
        try:
            if Image is not None and ImageTk is not None:
                with Image.open(path) as im0:
                    im = im0.convert("RGBA")
                if size:
                    if RESAMPLE is not None:
                        im.thumbnail((size, size), RESAMPLE)
                    else:
                        im.thumbnail((size, size))
                ph = ImageTk.PhotoImage(im)
            elif not path.lower().endswith(".ico"):
                ph = tk.PhotoImage(file=path)
                if size and max(ph.width(), ph.height()) > size:
                    ph = ph.subsample(max(1, max(ph.width(), ph.height()) // size))
        except Exception:
            ph = None
    _img_cache[key] = ph
    return ph

def logo_data_uri(size=160):
    key = size or 0
    if key in _uri_cache:
        return _uri_cache[key]
    uri = ""
    path = LOGO_PNG or (LOGO_ICO if Image else None)
    if path:
        try:
            if Image:
                with Image.open(path) as im0:
                    im = im0.convert("RGBA")
                if RESAMPLE is not None:
                    im.thumbnail((size, size), RESAMPLE)
                else:
                    im.thumbnail((size, size))
                buf = io.BytesIO()
                im.save(buf, "PNG")
                data = buf.getvalue()
            else:
                with open(path, "rb") as f:
                    data = f.read()
            uri = "data:image/png;base64," + base64.b64encode(data).decode()
        except Exception:
            uri = ""
    _uri_cache[key] = uri
    return uri

def set_icon(win):
    try:
        if LOGO_ICO and os.name == "nt":
            win.iconbitmap(LOGO_ICO)
            return
    except tk.TclError:
        pass
    ph = load_logo_image(64)
    if ph is not None:
        try:
            win.iconphoto(True, ph)
        except tk.TclError:
            pass

# --------------------------------------------------------------------------- helpers
DS = {"paper": "A4", "orient": "portrait", "mt": 12, "ml": 12, "fs": 13, "title": "", "sign": True, "pn": True}
KL = {"I": "आय", "E": "खर्च"}
MS = ["जन.", "फ़र.", "मार्च", "अप्रैल", "मई", "जून", "जुला.", "अग.", "सित.", "अक्टू.", "नव.", "दिस."]
MN = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
HD = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]
RT = [("account", "खाता-वार (Account wise)"), ("head", "हेड-वार (Head wise Expense)"), ("date", "तारीख-वार (Date wise)"),
      ("day", "दिन-वार (Day wise)"), ("ledger", "खाता-बही (Ledger)"), ("credit", "Credit-वार"), ("debit", "Debit-वार"),
      ("month", "मासिक (Monthly)"), ("pl", "आय–खर्च (Income / Expense)"), ("year", "वार्षिक (Yearly)"),
      ("session", "सत्र-वार (अप्रैल–मार्च)")]
PAPER = {"A4": (210, 297), "A3": (297, 420), "A5": (148, 210), "Letter": (216, 279), "Legal": (216, 356)}
THEMES = {"": ("#5f3dc4", "🟣 Violet"), "sun": ("#d9480f", "🟠 Sunset"),
          "sea": ("#0b7285", "🟢 Ocean"), "rose": ("#a61e4d", "🌸 Rose"),
          "forest": ("#2b8a3e", "🌿 Forest"), "royal": ("#364fc7", "🔵 Royal")}
GL = 5
MAXR = 1000
MAXPREV = 3000
CR_COL, DR_COL = "#1b7f4b", "#b3402a"
CR_BG, DR_BG = "#e3f5ea", "#fde8e3"
INK, MUTED, GOLD = "#1f2933", "#5c6f69", "#ffb703"
PAL = {"acc": "#5f3dc4", "dark": "#432b8a", "tint": "#e9e3f9", "soft": "#f6f3fd", "bg": "#f4f1fb"}

def mix(c, t="#ffffff", w=0.5):
    a = [int(c[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(t[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * w) for x, y in zip(a, b))

def paise(x):
    try:
        value = Decimal(str(x or 0))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {x!r}") from exc
    if not value.is_finite():
        raise ValueError(f"Non-finite monetary value: {x!r}")
    tup = value.as_tuple()
    with localcontext() as ctx:
        ctx.prec = max(28, len(tup.digits) + abs(int(tup.exponent)) + 4)
        return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))

def pz(x):
    if isinstance(x, float) and -1e13 <= x <= 1e13:
        y = x * 100.0
        p = round(y)
        if abs(y - p) < 0.01:
            return p
    return paise(x)

def rup(p):
    return p / 100

def r2(x):
    return paise(x) / 100

def fmt(n):
    n = r2(n)
    if n == 0:
        n = 0.0
    neg = n < 0
    ip, fp = f"{abs(n):.2f}".split(".")
    if len(ip) > 3:
        head, tail, groups = ip[:-3], ip[-3:], []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        ip = ",".join(groups + [tail])
    return ("-" if neg else "") + ip + "." + fp

def today():
    return datetime.date.today().isoformat()

def dmy(d):
    if not d:
        return ""
    if not isinstance(d, str):
        try:
            d = str(d)
        except Exception:
            return ""
    parts = d.split("-")
    if len(parts) != 3:
        return d
    try:
        y, mo, da = parts
        return f"{da}-{mo}-{y}"
    except Exception:
        return d

def dn(d):
    return HD[datetime.date.fromisoformat(d).weekday()]

def parse_date(s):
    if not isinstance(s, str):
        return None
    s = (s or "").strip()
    if not s:
        return ""
    m = re.fullmatch(r"(\d{1,2})([-/.])(\d{1,2})\2(\d{4})", s)
    try:
        if m:
            return datetime.date(int(m[4]), int(m[3]), int(m[1])).isoformat()
        if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", s):
            y, mo, d = map(int, s.split("-"))
            return datetime.date(y, mo, d).isoformat()
    except ValueError:
        pass
    return None

def numstr(x):
    return f"{r2(x):.2f}".rstrip("0").rstrip(".") or "0"

def parse_amt(s):
    try:
        raw = str(s).strip()
        number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
        indian_grouped = r"[+-]?\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d*)?"
        western_grouped = r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d*)?"
        if not any(re.fullmatch(pattern, raw) for pattern in (number, indian_grouped, western_grouped)):
            return None
        v = Decimal(raw.replace(",", ""))
        if not v.is_finite() or abs(v) > Decimal("1e13"):
            return None
        return r2(v)
    except (InvalidOperation, ValueError, OverflowError):
        return None

def uid():
    return format(int(time.time() * 1000), "x") + secrets.token_hex(4)

def atomic_write(path, writer, **kw):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".sap_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", **kw) as f:
            writer(f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise

def norm(s):
    return re.sub(r"\s+", " ", str(s).lower()).strip()

def record_fee_income(school_id, school_name, transaction_id, pay_date, amount,
                      student_name, student_class="", fee_details="", db_path=None):
    date = parse_date(pay_date)
    amount = parse_amt(amount)
    if not date or amount is None or amount <= 0:
        raise ValueError("Fee date or amount is invalid.")
    if school_id in (None, "") or transaction_id in (None, ""):
        raise ValueError("School and transaction IDs are required.")

    path = db_path or DB_FILE
    legacy = os.path.join(os.path.dirname(os.path.abspath(path)), "smart_account_data.json")
    core = Core(path, legacy)
    try:
        data = core.db
        office_id = f"feebook-school-{school_id}"
        office = next((o for o in data["offices"] if o["id"] == office_id), None)
        if office is None:
            office = {"id": office_id, "name": str(school_name or "School"), "addr": ""}
            data["offices"].append(office)
        else:
            office["name"] = str(school_name or office["name"] or "School")

        account = next(
            (a for a in data["accounts"]
             if a["oid"] == office_id and norm(a.get("name", "")) == "fees collection"),
            None
        )
        if account is None:
            account = {"id": uid(), "oid": office_id, "name": "Fees Collection",
                       "open": 0.0, "kind": "I", "head": "Fees", "code": "100"}
            data["accounts"].append(account)
        else:
            account["kind"] = "I"
            if not account.get("head"):
                account["head"] = "Fees"
            if not account.get("code"):
                account["code"] = "100"

        source_id = f"feebook:{school_id}:{transaction_id}"
        note_parts = [
            f"FeeBook receipt #{transaction_id}",
            f"Student: {student_name or 'Unknown'}",
        ]
        if student_class:
            note_parts.append(f"Class: {student_class}")
        if fee_details:
            note_parts.append(str(fee_details))
        entry = next((t for t in data["tx"] if t["id"] == source_id), None)
        voucher_no = (
            entry.get("vno") if entry is not None else
            max((t.get("vno") or 0 for t in data["tx"] if t["oid"] == office_id), default=0) + 1
        )
        values = {
            "oid": office_id,
            "vno": voucher_no,
            "aid": account["id"],
            "type": "C",
            "date": date,
            "amt": r2(amount),
            "note": " | ".join(note_parts),
        }
        if entry is None:
            data["tx"].append({"id": source_id, **values})
        else:
            entry.update(values)

        if not core.save():
            raise OSError(f"Could not save fee income to SAP: {core.err}")
    finally:
        core.close()
    return source_id

def delete_fee_income(school_id, transaction_id, db_path=None):
    if school_id in (None, ""):
        raise ValueError("School ID is required.")
    is_batch = isinstance(transaction_id, (list, tuple, set))
    transaction_ids = transaction_id if is_batch else [transaction_id]
    source_ids = {
        f"feebook:{school_id}:{transaction_id}"
        for transaction_id in transaction_ids
        if transaction_id not in (None, "")
    }
    if not source_ids:
        return 0 if is_batch else False
    path = db_path or DB_FILE
    legacy = os.path.join(os.path.dirname(os.path.abspath(path)), "smart_account_data.json")
    core = Core(path, legacy)
    try:
        remaining = [t for t in core.db["tx"] if t["id"] not in source_ids]
        removed = len(core.db["tx"]) - len(remaining)
        if removed == 0:
            return 0 if is_batch else False
        core.db["tx"] = remaining
        if not core.save():
            raise OSError(f"Could not remove fee income from SAP: {core.err}")
    finally:
        core.close()
    return removed if is_batch else True

# --------------------------------------------------------------------------- core
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS offices(seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, name TEXT, addr TEXT);
CREATE TABLE IF NOT EXISTS accounts(seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, oid TEXT, name TEXT, open REAL, kind TEXT, head TEXT, code TEXT);
CREATE TABLE IF NOT EXISTS tx(seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, oid TEXT, vno INTEGER, aid TEXT,
                              type TEXT, date TEXT, amt REAL, note TEXT, tid TEXT);
CREATE INDEX IF NOT EXISTS ix_tx_oid_date ON tx(oid, date);
CREATE INDEX IF NOT EXISTS ix_tx_aid ON tx(aid);
CREATE INDEX IF NOT EXISTS ix_tx_tid ON tx(tid);
CREATE INDEX IF NOT EXISTS ix_acc_oid ON accounts(oid);
"""
TB = {"offices": ("id", "name", "addr"),
      "accounts": ("id", "oid", "name", "open", "kind", "head", "code"),
      "tx": ("id", "oid", "vno", "aid", "type", "date", "amt", "note", "tid")}

class Core:
    skipped = 0

    def __init__(self, path, legacy=None, check=False):
        self.path = path
        self.err = ""
        self.con = sqlite3.connect(path, timeout=15)
        try:
            if check:
                res = self.con.execute("PRAGMA quick_check(1)").fetchone()
                if not res or res[0] != "ok":
                    raise sqlite3.DatabaseError("integrity check failed: %s" % (res[0] if res else "?"))
            for q in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=FULL", "PRAGMA temp_store=MEMORY", "PRAGMA cache_size=-20000"):
                self.con.execute(q)
            tx_columns = {row[1] for row in self.con.execute("PRAGMA table_info(tx)")}
            if tx_columns and "tid" not in tx_columns:
                self.con.execute("ALTER TABLE tx ADD COLUMN tid TEXT")
                self.con.commit()
            self.con.executescript(SCHEMA)
            try:
                self.con.execute("ALTER TABLE accounts ADD COLUMN head TEXT")
                self.con.commit()
            except sqlite3.OperationalError:
                pass
            try:
                self.con.execute("ALTER TABLE accounts ADD COLUMN code TEXT")
                self.con.commit()
            except sqlite3.OperationalError:
                pass
        except sqlite3.OperationalError:
            self.con.close()
            raise
        except sqlite3.DatabaseError as exc:
            self.con.close()
            log_error(f"sap.db kharab: {exc}\n{traceback.format_exc()}")
            raise RuntimeError("sap.db file corrupt hai. sap_auto_backup folder ki newest .db file load karein.") from exc
        self._snap = {"offices": {}, "accounts": {}, "tx": {}, "meta": {}}
        self._c = {}
        self._db = self.read(self.con)
        self._snapshot()
        done = self.con.execute("SELECT 1 FROM meta WHERE key='legacy_imported'").fetchone()
        imported_legacy = False
        if not done and (self._db["offices"] or self._db["tx"]):
            self._mark_legacy()
        elif not done and legacy and os.path.exists(legacy):
            try:
                with open(legacy, encoding="utf-8") as f:
                    self._db = self.clean(json.load(f))
                imported_legacy = True
            except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
                log_error(f"Legacy data import failed: {legacy}\n{traceback.format_exc()}")
        if self.mig() and imported_legacy:
            self._mark_legacy()
        self._data_version = self.con.execute("PRAGMA data_version").fetchone()[0]

    def _mark_legacy(self):
        try:
            with self.con:
                self.con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('legacy_imported','1')")
        except sqlite3.Error:
            log_error(traceback.format_exc())

    @property
    def db(self):
        return self._db

    @db.setter
    def db(self, v):
        self._db = v
        self._dirty()

    def _dirty(self):
        self._c = {}

    @staticmethod
    def read(con):
        db: dict[str, Any] = {"offices": [], "accounts": [], "tx": []}
        for r in con.execute("SELECT id,name,addr FROM offices ORDER BY seq"):
            db["offices"].append({"id": r[0], "name": r[1] or "", "addr": r[2] or ""})
        account_columns = {row[1] for row in con.execute("PRAGMA table_info(accounts)")}
        head_col = "head" if "head" in account_columns else "''"
        code_col = "code" if "code" in account_columns else "''"
        for r in con.execute(f"SELECT id,oid,name,open,kind,{head_col},{code_col} FROM accounts ORDER BY seq"):
            db["accounts"].append({"id": r[0], "oid": r[1], "name": r[2] or "", "open": r[3] or 0.0, "kind": r[4], "head": r[5] or "", "code": r[6] or ""})
        tx_columns = {row[1] for row in con.execute("PRAGMA table_info(tx)")}
        tid_col = "tid" if "tid" in tx_columns else "NULL"
        for r in con.execute(f"SELECT id,oid,vno,aid,type,date,amt,note,{tid_col} FROM tx ORDER BY seq"):
            d = {"id": r[0], "oid": r[1], "vno": r[2], "aid": r[3], "type": r[4], "date": r[5], "amt": r[6] or 0.0, "note": r[7] or ""}
            if r[8]:
                d["tid"] = r[8]
            db["tx"].append(d)
        meta = dict(con.execute("SELECT key,value FROM meta"))
        db["cur"] = meta.get("cur") or None
        db["theme"] = meta.get("theme") or ""
        db["lastBk"] = meta.get("lastBk") or None
        for k in ("setup", "seeded"):
            try:
                db[k] = json.loads(meta[k])
            except Exception:
                pass
        return Core.clean(db)

    @staticmethod
    def _date_ok(d):
        return isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) is not None and parse_date(d) == d

    @staticmethod
    def clean(db):
        if not isinstance(db, dict):
            db = {}
        n_in = {k: (len(db[k]) if isinstance(db.get(k), list) else 0) for k in ("offices", "accounts", "tx")}
        setup = db.get("setup")
        setup = {**DS, **(setup if isinstance(setup, dict) else {})}

        def bounded_setting(value, default, lo, hi):
            try:
                value = float(value)
                return min(hi, max(lo, value)) if math.isfinite(value) else default
            except (TypeError, ValueError, OverflowError):
                return default

        setup["paper"] = setup["paper"] if isinstance(setup["paper"], str) and setup["paper"] in PAPER else DS["paper"]
        setup["orient"] = setup["orient"] if isinstance(setup["orient"], str) and setup["orient"] in ("portrait", "landscape") else DS["orient"]
        setup["mt"] = bounded_setting(setup["mt"], DS["mt"], 0, 50)
        setup["ml"] = bounded_setting(setup["ml"], DS["ml"], 0, 50)
        setup["fs"] = bounded_setting(setup["fs"], DS["fs"], 8, 22)
        setup["title"] = str(setup["title"] or "")
        setup["sign"] = setup["sign"] if isinstance(setup["sign"], bool) else DS["sign"]
        setup["pn"] = setup["pn"] if isinstance(setup["pn"], bool) else DS["pn"]
        db["setup"] = setup
        db["theme"] = db.get("theme") if isinstance(db.get("theme"), str) and db.get("theme") in THEMES else ""
        lb = db.get("lastBk")
        db["lastBk"] = lb if Core._date_ok(lb) else None
        sd = db.get("seeded")
        db["seeded"] = [str(x) for x in sd] if isinstance(sd, list) else []

        def rows(key, need):
            out, seen = [], set()
            lst = db.get(key)
            for r in lst if isinstance(lst, list) else []:
                if not isinstance(r, dict) or any(k not in r or r.get(k) is None for k in need):
                    continue
                r["id"] = str(r["id"])
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                out.append(r)
            return out

        def num(v):
            try:
                v = float(v or 0)
            except (TypeError, ValueError, OverflowError):
                return 0.0
            return r2(v) if math.isfinite(v) and abs(v) <= 1e13 else 0.0

        offices = [o for o in rows("offices", ("id",)) if o["id"].strip()]
        office_ids = {o["id"] for o in offices}
        for o in offices:
            o["name"], o["addr"] = str(o.get("name") or ""), str(o.get("addr") or "")
        accounts = [a for a in rows("accounts", ("id", "oid"))
                    if a["id"].strip() and str(a["oid"]).strip() and str(a["oid"]) in office_ids]
        for a in accounts:
            a["oid"], a["name"], a["open"] = str(a["oid"]), str(a.get("name") or ""), num(a.get("open"))
            if not a.get("head"):
                a["head"] = "Fees" if a.get("kind") == "I" else "Other"
            a["code"] = str(a.get("code") or "").strip()
        account_by_id = {a["id"]: a for a in accounts}
        txs = []
        for t in rows("tx", ("id", "oid", "aid", "date", "amt")):
            if not t["id"].strip() or not str(t["oid"]).strip() or not str(t["aid"]).strip():
                continue
            if t.get("type") not in ("C", "D") or not Core._date_ok(t["date"]):
                continue
            aid = str(t["aid"])
            account = account_by_id.get(aid)
            if account is None:
                continue
            if isinstance(t["amt"], bool):
                continue
            try:
                raw_amount = float(t["amt"])
            except (TypeError, ValueError, OverflowError):
                continue
            if not math.isfinite(raw_amount) or abs(raw_amount) > 1e13:
                continue
            amount = r2(raw_amount)
            if amount < 0:
                continue
            t["oid"], t["aid"], t["amt"] = account["oid"], aid, amount
            try:
                vno = Decimal(str(t["vno"])) if t.get("vno") not in (None, "") else None
                t["vno"] = (int(vno) if vno is not None and vno.is_finite()
                            and vno == vno.to_integral_value() and 0 <= vno < 2**63 - 1 else None)
            except (InvalidOperation, TypeError, ValueError, OverflowError):
                t["vno"] = None
            t["note"] = str(t.get("note") or "")
            if t.get("tid"):
                t["tid"] = str(t["tid"])
            else:
                t.pop("tid", None)
            txs.append(t)
        db["offices"], db["accounts"], db["tx"] = offices, accounts, txs
        Core.skipped += sum(max(0, n_in[k] - len(db[k])) for k in n_in)
        if not any(o["id"] == db.get("cur") for o in offices):
            db["cur"] = offices[0]["id"] if offices else None
        return db

    @staticmethod
    def _row(tb, d):
        if tb == "offices":
            return (d["id"], d.get("name") or "", d.get("addr") or "")
        if tb == "accounts":
            return (d["id"], d["oid"], d.get("name") or "", float(d.get("open") or 0), d.get("kind") or "E", d.get("head") or ("Fees" if d.get("kind") == "I" else "Other"), str(d.get("code") or ""))
        return (d["id"], d["oid"], d.get("vno"), d["aid"], d["type"], d["date"], float(d.get("amt") or 0), d.get("note") or "", d.get("tid") or None)

    def _meta(self):
        d = self._db
        return {"cur": d.get("cur") or "", "theme": d.get("theme") or "", "lastBk": d.get("lastBk") or "",
                "setup": json.dumps(d["setup"], ensure_ascii=False, sort_keys=True), "seeded": json.dumps(d["seeded"])}

    def _snapshot(self):
        self._snap = {tb: {d["id"]: self._row(tb, d) for d in self._db[tb]} for tb in TB}
        self._snap["meta"] = self._meta()

    def _flush(self):
        new = {}
        for tb, cols in TB.items():
            cur = {d["id"]: self._row(tb, d) for d in self._db[tb]}
            old = self._snap[tb]
            dele = [(i,) for i in old if i not in cur]
            add = [r for i, r in cur.items() if i not in old]
            upd = [r[1:] + (r[0],) for i, r in cur.items() if i in old and old[i] != r]
            if dele:
                self.con.executemany(f"DELETE FROM {tb} WHERE id=?", dele)
            if upd:
                self.con.executemany(f"UPDATE {tb} SET {','.join(c + '=?' for c in cols[1:])} WHERE id=?", upd)
            if add:
                self.con.executemany(f"INSERT INTO {tb}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", add)
            new[tb] = cur
        meta = self._meta()
        for k, v in meta.items():
            if self._snap["meta"].get(k) != v:
                self.con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (k, v))
        new["meta"] = meta
        return new

    def save(self):
        try:
            with self.con:
                new = self._flush()
            self._snap = new
            self.err = ""
            return True
        except Exception as e:
            self.err = f"{type(e).__name__}: {e}"
            log_error(traceback.format_exc())
            return False
        finally:
            self._dirty()

    def refresh_external(self):
        version = self.con.execute("PRAGMA data_version").fetchone()[0]
        if version == self._data_version:
            return False
        self.db = self.read(self.con)
        self._snapshot()
        self._data_version = version
        return True

    def replace_all(self, newdb):
        newdb = self.clean(newdb)
        old_db, old_snap = self._db, self._snap
        try:
            with self.con:
                for tb in TB:
                    self.con.execute(f"DELETE FROM {tb}")
                self.con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('legacy_imported','1')")
                self._snap = {"offices": {}, "accounts": {}, "tx": {}, "meta": old_snap["meta"]}
                self._db = newdb
                self._mig_data()
                new = self._flush()
        except Exception:
            self._db, self._snap = old_db, old_snap
            self._dirty()
            raise
        self._snap = new
        self._dirty()

    def export_db(self, dest):
        dst = sqlite3.connect(dest)
        try:
            self.con.backup(dst)
            dst.execute("PRAGMA journal_mode=DELETE")
        finally:
            dst.close()

    def snapshot(self, folder, name, prefix, keep, skip_existing=False):
        os.makedirs(folder, exist_ok=True)
        final = os.path.join(folder, name + ".db")
        if skip_existing and os.path.exists(final):
            return final
        tmp = final + ".tmp"
        if os.path.exists(tmp):
            os.remove(tmp)
        self.export_db(tmp)
        os.replace(tmp, final)
        old = sorted(glob.glob(os.path.join(glob.escape(folder), glob.escape(prefix) + "*.db")))
        for p in old[:-keep] if keep > 0 else []:
            try:
                os.remove(p)
            except OSError:
                pass
        return final

    def close(self):
        if self.con is None:
            self._c.clear()
            self._db = {"offices": [], "accounts": [], "tx": [], "cur": None, "setup": dict(DS), "theme": ""}
            return
        try:
            self.save()
            self.con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        finally:
            self._c.clear()
            self._db = {"offices": [], "accounts": [], "tx": [], "cur": None, "setup": dict(DS), "theme": ""}
            try:
                self.con.close()
            except sqlite3.Error:
                pass

    def _mig_data(self):
        db = self.db
        for a in db["accounts"]:
            if a.get("kind") not in ("I", "E"):
                a["kind"] = "I" if re.fullmatch(r"\s*(fees?\s*collection|return\s*payment)\s*", a["name"], re.I) else "E"
            if not a.get("head"):
                a["head"] = "Fees" if a["kind"] == "I" else "Other"
            if not str(a.get("code") or "").strip():
                a["code"] = ""

        # Account codes must be unique within an office, including imported data.
        for o in db["offices"]:
            oid = o["id"]
            o_accs = [a for a in db["accounts"] if a["oid"] == oid]
            used_codes = set()
            next_num = 101
            for a in o_accs:
                code = str(a.get("code") or "").strip()
                code_key = norm(code)
                if not code or code_key in used_codes:
                    while norm(str(next_num)) in used_codes:
                        next_num += 1
                    code = a["code"] = str(next_num)
                    code_key = norm(code)
                    next_num += 1
                used_codes.add(code_key)

        for o in db["offices"]:
            if o["id"] in db["seeded"]:
                continue
            db["seeded"].append(o["id"])
            if not any(a["oid"] == o["id"] and a["name"].strip().lower() == "return payment" for a in db["accounts"]):
                used_codes = {norm(a.get("code", "")) for a in db["accounts"] if a["oid"] == o["id"]}
                code = "999"
                while norm(code) in used_codes:
                    code = str(int(code) + 1)
                db["accounts"].append({"id": uid(), "oid": o["id"], "name": "Return Payment", "open": 0.0, "kind": "I", "head": "Return", "code": code})

    def mig(self):
        self._mig_data()
        return self.save()

    def office(self):
        return next((o for o in self.db["offices"] if o["id"] == self.db["cur"]), None)

    def accs(self):
        k = ("accs", self.db["cur"])
        if k not in self._c:
            self._c[k] = [a for a in self.db["accounts"] if a["oid"] == self.db["cur"]]
        return self._c[k]

    def txs(self):
        k = ("txs", self.db["cur"])
        if k not in self._c:
            self._c[k] = [t for t in self.db["tx"] if t["oid"] == self.db["cur"]]
        return self._c[k]

    def _st(self):
        if "st" not in self._c:
            net, ex, dn_ = {}, {}, {}
            for t in self.db["tx"]:
                a, p = t["aid"], pz(t["amt"])
                c = t["type"] == "C"
                n = p if c else -p
                net[a] = net.get(a, 0) + n
                if t.get("tid"):
                    ex[a] = ex.get(a, 0) + n
                else:
                    ex[a] = ex.get(a, 0) + (-n)
                    dn_[a] = dn_.get(a, 0) + n
            self._c["st"] = (net, ex, dn_)
        return self._c["st"]

    def acc(self, aid):
        m = self._c.get("amap")
        if m is None:
            m = self._c["amap"] = {a["id"]: a for a in self.db["accounts"]}
        return m.get(aid)

    def name(self, aid):
        a = self.acc(aid)
        return a["name"] if a else "?"

    @staticmethod
    def kd(a):
        return "I" if a and a.get("kind") == "I" else "E"

    def kind_of(self, aid):
        return self.kd(self.acc(aid))

    def by_kind(self, A):
        return [a for a in A if self.kd(a) == "I"] + [a for a in A if self.kd(a) != "I"]

    def next_v(self):
        return max([t.get("vno") or 0 for t in self.txs()] + [0]) + 1

    @staticmethod
    def pnet(t):
        a = pz(t["amt"])
        return a if t["type"] == "C" else -a

    @staticmethod
    def pex(t):
        a = pz(t["amt"])
        if t.get("tid"):
            return a if t["type"] == "C" else -a
        return a if t["type"] == "D" else -a

    @staticmethod
    def pdn(t):
        return 0 if t.get("tid") else Core.pnet(t)

    @staticmethod
    def net(t):
        return rup(Core.pnet(t))

    @staticmethod
    def exT(t):
        return rup(Core.pex(t))

    def dnT(self, t):
        return rup(Core.pdn(t))

    def bal(self, a):
        if isinstance(a, str):
            a = self.acc(a) or {"id": a, "open": 0.0}
        if not isinstance(a, dict):
            return 0.0
        aid = a.get("id")
        if not aid:
            return 0.0
        return rup(pz(a.get("open") or 0.0) + self._st()[0].get(aid, 0))

    def spent(self, a):
        if isinstance(a, str):
            a = self.acc(a) or {"id": a}
        if not isinstance(a, dict):
            return 0.0
        aid = a.get("id")
        if not aid:
            return 0.0
        return rup(pz(a.get("open") or 0.0) + self._st()[1].get(aid, 0))

    def remaining(self):
        tot = 0
        net, _ex, dn_ = self._st()
        for a in self.accs():
            if self.kd(a) == "I":
                tot += pz(a.get("open") or 0.0) + net.get(a["id"], 0)
            else:
                tot -= pz(a.get("open") or 0.0)
                tot += dn_.get(a["id"], 0)
        return rup(tot)

    def pl(self, frm="", to=""):
        key = ("pl", self.db["cur"], frm, to)
        if key in self._c:
            return dict(self._c[key])
        k = {a["id"]: self.kd(a) for a in self.accs()}
        pp = self._c.get("pp")
        if pp is None:
            pp = self._c["pp"] = [(t["aid"], t["date"], self.pnet(t), self.pex(t), bool(t.get("tid"))) for t in self.txs()]
        i = e = 0
        for aid, date, n, x, tid in pp:
            if aid not in k or (frm and date < frm) or (to and date > to):
                continue
            if k[aid] == "I":
                if not tid:
                    i += n
            else:
                e += x
        res = {"i": rup(i), "e": rup(e), "n": rup(i - e)}
        self._c[key] = res
        return dict(res)

    def hay(self, t):
        h = self._c.setdefault("hay", {})
        if t["id"] not in h:
            h[t["id"]] = self._hay(t)
        return h[t["id"]]

    def _hay(self, t):
        acc = self.acc(t["aid"])
        head = acc.get("head", "") if acc else ""
        code = acc.get("code", "") if acc else ""
        return norm(" ".join(str(x) for x in [
            t.get("note", ""), self.name(t["aid"]), head, code, t["amt"], f"{t['amt']:.2f}", fmt(t["amt"]), t.get("vno") or "",
            dmy(t["date"]), t["date"], "credit jama" if t["type"] == "C" else "debit name", KL[self.kind_of(t["aid"])]]))

    def hit(self, t, q):
        words = norm(q or "").split()
        if not words:
            return True
        h = self.hay(t)
        return all(w in h for w in words)

    def last_tx(self, q="", td=False):
        ix = {t["id"]: i for i, t in enumerate(self.db["tx"])}
        g, sr, tdy = {}, bool(q and q.strip()), today()
        for t in self.txs():
            if self.hit(t, q) and (not td or t["date"] == tdy):
                g.setdefault(t.get("tid") or t["id"], []).append(t)
        gs = [sorted(v, key=lambda x: ix[x["id"]]) for v in g.values()]
        gs.sort(key=lambda a: (a[0]["date"], ix[a[0]["id"]]), reverse=True)
        sel = gs if (sr or td) else gs[:GL]
        return [t for grp in sel for t in grp], len(gs), sr

    def report(self, rp):
        o, A = self.office(), self.accs()
        S = [a for a in A if a["id"] == rp["aid"]] if rp["aid"] else A
        ids = {a["id"] for a in S}
        allt = [t for t in self.txs() if t["aid"] in ids]
        frm, to = rp["from"], rp["to"]

        # Smart Name Filtering (Normalized & Case-Insensitive Security with exact word/substring matching)
        name_filter = norm(rp.get("name_filter", ""))

        def tx_matches_name_filter(t):
            if not name_filter:
                return True
            acc = self.acc(t["aid"])
            haystack = " ".join(str(x) for x in [
                self.name(t["aid"]),
                acc.get("name", "") if acc else "",
                acc.get("head", "") if acc else "",
                acc.get("code", "") if acc else "",
                t.get("note", ""),
                t.get("vno") or "",
                t.get("tid") or "",
            ])
            return name_filter in norm(haystack)

        filtered_txs = []
        for t in allt:
            if frm and t["date"] < frm:
                continue
            if to and t["date"] > to:
                continue
            if not tx_matches_name_filter(t):
                continue
            filtered_txs.append(t)

        L = sorted(filtered_txs, key=lambda t: t["date"])
        by_all, by_L = {}, {}
        for t in allt:
            by_all.setdefault(t["aid"], []).append(t)
        for t in L:
            by_L.setdefault(t["aid"], []).append(t)
        kmap = {a["id"]: self.kd(a) for a in S}
        isI = lambda a: self.kd(a) == "I"
        agg = len(S) > 1
        oneE = len(S) == 1 and not isI(S[0])
        amt = lambda t: pz(t["amt"])
        pnet, pex, pdn = self.pnet, self.pex, self.pdn
        st = lambda t: pnet(t) if kmap[t["aid"]] == "I" else (pdn(t) if agg else pex(t))
        sum_ = lambda l, ty: sum(amt(t) for t in l if t["type"] == ty)
        bef = lambda l, f: sum(f(t) for t in l if frm and t["date"] < frm)
        exAdd = lambda l: sum(amt(t) for t in l if pex(t) > 0)
        exRed = lambda l: sum(amt(t) for t in l if pex(t) < 0)
        ntC = lambda l: sum(amt(t) for t in l if kmap[t["aid"]] == "I" and t["type"] == "C" and not t.get("tid"))
        title = dict(RT)[rp["type"]]
        note = ""

        def opening():
            return sum((pz(a["open"]) if isI(a) or not agg else -pz(a["open"])) + bef(by_all.get(a["id"], []), st) for a in S)

        ty = rp["type"]
        if ty == "account":
            H = ["Code", "खाता", "Head", "Opening", "Credit", "Debit", "Closing"]
            R, tot = [], [0, 0, 0, 0]
            for a in S:
                ls, l = by_all.get(a["id"], []), by_L.get(a["id"], [])
                nm = a["name"] + (f" ({KL[self.kd(a)]})" if agg else "")
                head = a.get("head", "-")
                code = a.get("code", "-") or "-"
                if isI(a):
                    op, c, d = pz(a["open"]) + bef(ls, pnet), sum_(l, "C"), sum_(l, "D")
                    close_amt = op + c - d
                else:
                    op, c, d = pz(a["open"]) + bef(ls, pex), exRed(l), exAdd(l)
                    close_amt = op + d - c
                R.append([code, nm, head, rup(op), rup(c), rup(d), rup(close_amt)])
                for i, v in enumerate((op, c, d, close_amt)):
                    tot[i] += v
            if agg:
                op = opening()
                e = op + sum(st(t) for t in L)
                cr = ntC(L)
                F = ["कुल (खर्च निकालकर)", "", "", rup(op), rup(cr), rup(op + cr - e), rup(e)]
            else:
                F = ["कुल", "", ""] + [rup(x) for x in tot]
            if any(not isI(a) for a in S):
                note = "नोट: खर्च खाते का Opening Balance शुरुआती खर्च है; Debit = खर्च, Credit = वापसी/घटत, Closing = कुल खर्च।"
                if agg:
                    note += ' अंतिम "कुल" पंक्ति = बचा हुआ पैसा (आय − खर्च)।'
        elif ty == "head":
            H = ["Expense Head", "खातों की संख्या", "कुल खर्च (₹)"]
            head_map = {}
            for a in (S if rp["aid"] else A):
                if self.kd(a) == "E":
                    h_name = a.get("head", "Other") or "Other"
                    l = by_L.get(a["id"], [])
                    exp_amt = sum(pex(t) for t in l)
                    if h_name not in head_map:
                        head_map[h_name] = {"count": 0, "amt": 0}
                    head_map[h_name]["count"] += 1
                    head_map[h_name]["amt"] += exp_amt
            R = []
            tot_amt = 0
            for h_name, data in sorted(head_map.items()):
                R.append([h_name, data["count"], rup(data["amt"])])
                tot_amt += data["amt"]
            F = ["कुल खर्च Head-wise", "", rup(tot_amt)]
            note = "यह रिपोर्ट आपके द्वारा निर्धारित किए गए खर्च Heads के आधार पर सटीक विवरण दिखाती है।"
        elif ty == "pl":
            def account_net(a):
                l = by_L.get(a["id"], [])
                if self.kd(a) != "I":
                    return sum(pex(t) for t in l)
                l = [t for t in l if not t.get("tid")]
                return sum_(l, "C") - sum_(l, "D")
            ri = [["आय", a.get("code", "-"), a["name"], account_net(a)] for a in S if self.kd(a) == "I"]
            re_ = [["खर्च", a.get("code", "-"), a["name"], account_net(a)] for a in S if self.kd(a) != "I"]
            ti, te = sum(x[3] for x in ri), sum(x[3] for x in re_)
            H = ["श्रेणी", "Code", "खाता", "राशि"]
            R = [[x[0], x[1], x[2], rup(x[3])] for x in ri] + [["", "", "कुल आय", rup(ti)]] + \
                [[x[0], x[1], x[2], rup(x[3])] for x in re_] + [["", "", "कुल खर्च", rup(te)]]
            F = ["", "", "शुद्ध बचत (आय − खर्च)", rup(ti - te)]
        elif ty == "ledger":
            H = ["तारीख", "Code", "खाता", "Head", "विवरण", "Credit", "Debit", "कुल खर्च" if oneE else "Balance"]
            b = opening()
            R = [["", "", "", "", "पिछला खर्च (शुरू तक)" if oneE else "Opening Balance", "", "", rup(b)]]
            for t in L:
                b += st(t)
                a_ = amt(t)
                acc = self.acc(t["aid"])
                code = acc.get("code", "-") if acc else "-"
                head = acc.get("head", "") if acc else ""
                R.append([dmy(t["date"]), code, self.name(t["aid"]), head, t.get("note", ""),
                          rup(a_) if t["type"] == "C" else "", rup(a_) if t["type"] == "D" else "", rup(b)])
            F = ["", "", "", "", "कुल", rup(sum_(L, "C")), rup(sum_(L, "D")), rup(b)]
        elif ty in ("date", "credit", "debit"):
            one = ty != "date"
            l = [t for t in L if t["type"] == "C"] if ty == "credit" else [t for t in L if t["type"] == "D"] if ty == "debit" else L
            H = ["#", "तारीख", "Code", "खाता", "Head", "विवरण", "राशि"] if one else ["#", "तारीख", "Code", "खाता", "Head", "विवरण", "Credit", "Debit"]
            R = []
            for i, t in enumerate(l, 1):
                acc = self.acc(t["aid"])
                code = acc.get("code", "-") if acc else "-"
                head = acc.get("head", "") if acc else ""
                b = [str(i), dmy(t["date"]), code, self.name(t["aid"]), head, t.get("note", "")]
                a_ = rup(amt(t))
                R.append(b + [a_] if one else b + [a_ if t["type"] == "C" else "", a_ if t["type"] == "D" else ""])
            F = ["", "", "", "", "", "कुल", rup(sum(amt(t) for t in l))] if one else ["", "", "", "", "", "कुल", rup(sum_(l, "C")), rup(sum_(l, "D"))]
        else:
            def sess(d):
                y, mo = int(d[:4]), int(d[5:7])
                return f"{y}-{(y + 1) % 100:02d}" if mo > 3 else f"{y - 1}-{y % 100:02d}"
            kf = {"day": lambda t: t["date"], "month": lambda t: t["date"][:7],
                  "year": lambda t: t["date"][:4], "session": lambda t: sess(t["date"])}[ty]
            lb = {"day": lambda k: f"{dmy(k)} ({dn(k)})", "month": lambda k: f"{MN[int(k[5:]) - 1]} {k[:4]}",
                  "year": lambda k: k, "session": lambda k: "सत्र " + k}[ty]
            g = {}
            for t in L:
                g.setdefault(kf(t), []).append(t)
            b = opening()
            op0 = b
            H = ["अवधि", "Opening", "Credit", "Debit", "Closing"]
            R, sc, sd = [], 0, 0
            for k in sorted(g):
                p = b
                for t in g[k]:
                    b += st(t)
                if agg:
                    c = ntC(g[k])
                    d = p + c - b
                elif oneE:
                    c, d = exRed(g[k]), exAdd(g[k])
                else:
                    c, d = sum_(g[k], "C"), sum_(g[k], "D")
                sc += c
                sd += d
                R.append([lb(k), rup(p), rup(c), rup(d), rup(b)])
            F = ["कुल", rup(op0), rup(sc), rup(sd), rup(b)]

        per = f"{dmy(frm) if frm else 'शुरू'} से {dmy(to) if to else 'आज तक'}" if (frm or to) else "सभी तारीख"
        acname = self.name(rp["aid"]) if rp["aid"] else "सभी"
        acc_obj = self.acc(rp["aid"]) if rp["aid"] else None
        if acc_obj and acc_obj.get("code"):
            acname = f"[{acc_obj['code']}] {acname}"
        if rp.get("name_filter"):
            per += f" | फ़िल्टर: {rp.get('name_filter')}"
        return {"H": H, "R": R, "F": F, "title": title, "per": per, "note": note, "acc": acname,
                "office": o["name"] if o else "", "addr": (o.get("addr") if o else "") or ""}

    @staticmethod
    def cell(c, i, F):
        if isinstance(c, (int, float)) and not isinstance(c, bool):
            return fmt(c)
        return str(c)

    def report_html(self, rep, logo_uri=""):
        s = self.db["setup"]
        H, R, F = rep["H"], rep["R"], rep["F"]
        numeric = [isinstance(x, (int, float)) for x in F]

        def td(c, i, tag="td"):
            is_code = (H[i] == "Code")
            cls = ' class="n"' if numeric[i] else (' class="c"' if is_code else "")
            return f"<{tag}{cls}>{'' if c == '' else escape(self.cell(c, i, F))}</{tag}>"
        w = PAPER.get(s["paper"], PAPER["A4"])
        w = w[1] if s["orient"] == "landscape" else w[0]
        pn = '@bottom-right{content:"पृष्ठ " counter(page) " / " counter(pages);font-size:9pt}' if s["pn"] else ""
        body = ""
        if R:
            body = ("<table><thead><tr>" + "".join(td(h, i, "th") for i, h in enumerate(H)) + "</tr></thead><tbody>" +
                    "".join("<tr>" + "".join(td(c, i) for i, c in enumerate(r)) + "</tr>" for r in R) +
                    "</tbody><tfoot><tr>" + "".join(td(c, i) for i, c in enumerate(F)) + "</tr></tfoot></table>")
            if rep["note"]:
                body += f'<div class="mut" style="font-size:.85em;margin-top:6px">{escape(rep["note"])}</div>'
        else:
            body = '<p class="mut" style="text-align:center">इस अवधि में कोई रिकॉर्ड नहीं</p>'
        sign = '<div class="sg"><span>तैयार करने वाला</span><span>जाँचकर्ता</span><span>अधिकृत हस्ताक्षर</span></div>' if s["sign"] else ""
        acc = THEMES.get(self.db.get("theme", ""), THEMES[""])[0]
        dark, tint = mix(acc, "#000000", 0.30), mix(acc, "#ffffff", 0.88)
        logo = f'<img class="lg" src="{logo_uri}" alt="">' if logo_uri else ""
        gap = '<span class="sp"></span>' if logo_uri else ""
        sub = " &nbsp;•&nbsp; ".join(escape(x) for x in (rep["addr"], s["title"]) if x)
        ad = f'<div class="ad">{sub}</div>' if sub else ""
        return f"""<!DOCTYPE html><html lang="hi"><head><meta charset="utf-8"><title>{escape(rep['title'])}</title><style>
@page{{size:{s['paper']} {s['orient']};margin:{s['mt']}mm {s['ml']}mm;{pn}}}
*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{font:{s['fs']}px/1.4 "Segoe UI","Noto Sans Devanagari",sans-serif;color:#17302b;margin:0}}
.sheet{{box-sizing:border-box;width:{w}mm;max-width:100%;margin:0 auto;padding:{s['mt']}mm {s['ml']}mm}}
@media print{{.sheet{{width:auto;max-width:none;padding:0}}}}
.sh{{display:flex;align-items:center;gap:12px;padding-bottom:6px;border-bottom:2px solid {acc}}}
.sh .lg{{width:46px;height:46px;object-fit:contain;flex:none}}.sh .sp{{width:46px;flex:none}}
.sh .ht{{flex:1;min-width:0;text-align:center}}.sh h1{{margin:0;font-size:1.45em;line-height:1.2;color:{dark}}}
.sh .ad{{font-size:.85em;color:#5c6f69}}
.ri{{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:4px 14px;margin:6px 0 8px;font-size:.92em}}
.ri b{{font-size:1.12em;color:{acc}}}.ri span{{color:#5c6f69}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:3px 7px;border-bottom:1px solid #d9dfdc;text-align:left}}
th{{background:{tint};color:{dark};border-top:2px solid {acc};border-bottom:2px solid {acc}}}
tbody tr:nth-child(even) td{{background:#f7f9f8}}.n{{text-align:right}}.c{{text-align:center}}
tfoot{{display:table-row-group}}tfoot td{{font-weight:700;background:{tint};border-top:2px solid {acc}}}.mut{{color:#5c6f69}}
.sg{{display:flex;justify-content:space-between;margin-top:40px;font-size:.9em}}
.sg span{{border-top:1px solid #000;padding-top:4px;min-width:28%;text-align:center}}
.pf{{margin-top:8px;font-size:.75em;color:#5c6f69;text-align:right}}
thead{{display:table-header-group}}tr{{break-inside:avoid}}
</style></head><body><div class="sheet"><div class="sh">{logo}<div class="ht"><h1>{escape(rep['office'])}</h1>{ad}</div>{gap}</div>
<div class="ri"><b>{escape(rep['title'])}</b><span>अवधि: {escape(rep['per'])} &nbsp;|&nbsp; खाता: {escape(rep['acc'])}</span></div>
{body}{sign}<div class="pf">Print: {datetime.datetime.now().strftime('%d/%m/%Y, %I:%M:%S %p')}</div></div>
<script>window.onload=function(){{setTimeout(function(){{window.print()}},400)}}</script></body></html>"""

# --------------------------------------------------------------------------- dialogs
def _center(d, parent):
    d.update_idletasks()
    p = parent.winfo_toplevel()
    x = p.winfo_rootx() + (p.winfo_width() - d.winfo_width()) // 2
    y = p.winfo_rooty() + (p.winfo_height() - d.winfo_height()) // 3
    x = max(0, min(x, d.winfo_screenwidth() - d.winfo_width()))
    y = max(0, min(y, d.winfo_screenheight() - d.winfo_height() - 40))
    d.geometry(f"+{x}+{y}")

def _dialog(parent, title):
    d = tk.Toplevel(parent)
    d.title(title)
    d.configure(bg=PAL["bg"])
    set_icon(d)
    d.transient(parent.winfo_toplevel())
    d.resizable(False, False)
    return d

def _modal(d):
    try:
        d.wait_visibility()
        d.grab_set()
    except tk.TclError:
        pass

def msgbox(parent, title, text, kind="info"):
    d = _dialog(parent, title)
    f = ttk.Frame(d, padding=16)
    f.pack()
    sym = {"info": "ℹ", "warn": "⚠", "error": "✖"}.get(kind, "ℹ")
    ttk.Label(f, text=sym, font=("Segoe UI", 24)).grid(row=0, column=0, padx=(0, 14))
    ttk.Label(f, text=text, wraplength=int(380 * K), justify="left").grid(row=0, column=1, sticky="w")
    b = ttk.Button(f, text="ठीक है", command=d.destroy)
    b.grid(row=1, column=0, columnspan=2, pady=(14, 0))
    d.bind("<Return>", lambda e: d.destroy())
    d.bind("<Escape>", lambda e: d.destroy())
    _center(d, parent)
    _modal(d)
    b.focus_set()
    d.wait_window()

def confirm(parent, title, text):
    d = _dialog(parent, title)
    res = [False]
    f = ttk.Frame(d, padding=16)
    f.pack()
    ttk.Label(f, text="❓", font=("Segoe UI", 24)).grid(row=0, column=0, padx=(0, 14))
    ttk.Label(f, text=text, wraplength=int(380 * K), justify="left").grid(row=0, column=1, sticky="w")
    bf = ttk.Frame(f)
    bf.grid(row=1, column=0, columnspan=2, pady=(14, 0))

    def yes():
        res[0] = True
        d.destroy()
    y = ttk.Button(bf, text="हाँ", command=yes)
    y.pack(side="left", padx=4)
    ttk.Button(bf, text="नहीं", command=d.destroy).pack(side="left", padx=4)
    d.bind("<Escape>", lambda e: d.destroy())
    _center(d, parent)
    _modal(d)
    y.focus_set()
    d.wait_window()
    return res[0]

def form_dialog(parent, title, fields):
    d = _dialog(parent, title)
    f = ttk.Frame(d, padding=16)
    f.pack()
    vs, first = [], None
    for i, fd in enumerate(fields):
        if fd[0] == "check":
            v = tk.BooleanVar(value=fd[2])
            ttk.Checkbutton(f, text=fd[1], variable=v).grid(row=i, column=0, columnspan=2, sticky="w", pady=3)
        else:
            ttk.Label(f, text=fd[1]).grid(row=i, column=0, sticky="w", padx=(0, 12), pady=3)
            v = tk.StringVar(value=str(fd[2]))
            w = (ttk.Combobox(f, textvariable=v, values=fd[3], state="readonly", width=28) if fd[0] == "choice"
                 else ttk.Entry(f, textvariable=v, width=32))
            w.grid(row=i, column=1, pady=3)
            if first is None:
                first = w
        vs.append(v)
    res: list[list[object] | None] = [None]

    def ok(_=None):
        res[0] = [v.get() for v in vs]
        d.destroy()
    bf = ttk.Frame(f)
    bf.grid(row=len(fields), column=0, columnspan=2, pady=(12, 0))
    ttk.Button(bf, text="ठीक है", command=ok).pack(side="left", padx=4)
    ttk.Button(bf, text="रद्द", command=d.destroy).pack(side="left", padx=4)
    d.bind("<Return>", ok)
    d.bind("<Escape>", lambda e: d.destroy())
    _center(d, parent)
    _modal(d)
    if first is not None:
        first.focus_set()
    d.wait_window()
    return res[0]

# --------------------------------------------------------------------------- widgets
class Flow(ttk.Frame):
    def __init__(self, parent, minw=240, sticky="nsew"):
        super().__init__(parent)
        self.minw, self.sticky, self.items, self.cols = minw, sticky, [], 0
        self.bind("<Configure>", lambda e: self.relayout())

    def add(self, w):
        self.items.append(w)
        self.cols = 0
        self.relayout()

    def relayout(self):
        n = max(1, min(len(self.items) or 1, int(self.winfo_width() // (self.minw * K))))
        if n == self.cols:
            return
        self.cols = n
        for c in range(12):
            self.columnconfigure(c, weight=0, uniform="")
        for c in range(n):
            self.columnconfigure(c, weight=1, uniform="f")
        for i, w in enumerate(self.items):
            w.grid(row=i // n, column=i % n, sticky=self.sticky, padx=4, pady=3)

def field(flow, label, cls, **kw):
    fr = ttk.Frame(flow)
    ttk.Label(fr, text=label).pack(anchor="w")
    w = cls(fr, **kw)
    w.pack(fill="x")
    flow.add(fr)
    return w

class ScrollFrame(ttk.Frame):
    _all = []
    _bound = False

    def __init__(self, parent):
        super().__init__(parent)
        self.cv = tk.Canvas(self, highlightthickness=0, bg=PAL["bg"], yscrollincrement=int(18 * K))
        sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.inner = ttk.Frame(self.cv, padding=8)
        self.win = self.cv.create_window((0, 0), window=self.inner, anchor="nw")
        self.cv.configure(yscrollcommand=sb.set)
        self.cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._sync)
        self.cv.bind("<Configure>", self._sync)
        ScrollFrame._all.append(self)
        self.bind("<Destroy>", self._on_destroy, add="+")
        if not ScrollFrame._bound:
            ScrollFrame._bound = True
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.bind_all(ev, ScrollFrame._wheel, add="+")

    def _sync(self, _=None):
        try:
            w, h = self.cv.winfo_width(), self.cv.winfo_height()
            hh = max(h, self.inner.winfo_reqheight())
            self.cv.itemconfigure(self.win, width=w, height=hh)
            self.cv.configure(scrollregion=(0, 0, w, hh))
        except tk.TclError:
            pass

    def _on_destroy(self, event):
        if event.widget is self and self in ScrollFrame._all:
            ScrollFrame._all.remove(self)
            if not ScrollFrame._all and ScrollFrame._bound:
                for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                    try:
                        self.unbind_all(ev)
                    except tk.TclError:
                        pass
                ScrollFrame._bound = False

    @staticmethod
    def _wheel(e):
        w = e.widget
        while w is not None and not isinstance(w, str):
            if isinstance(w, (ttk.Treeview, tk.Listbox, tk.Text)):
                return
            for sf in ScrollFrame._all:
                if w is sf:
                    if sf.cv.yview() != (0.0, 1.0):
                        up = e.num == 4 or getattr(e, "delta", 0) > 0
                        sf.cv.yview_scroll(-3 if up else 3, "units")
                    return
            w = getattr(w, "master", None)

_TREES = []

def tree_tags(tr):
    tr.tag_configure("odd", background=PAL["soft"])
    tr.tag_configure("cr", foreground=CR_COL)
    tr.tag_configure("dr", foreground=DR_COL)
    tr.tag_configure("foot", font=("Segoe UI", 10, "bold"), background=PAL["tint"], foreground=PAL["dark"])

def make_tree(parent, cols, height=8, xscroll=False):
    fr = ttk.Frame(parent)
    tr = ttk.Treeview(fr, columns=[c[0] for c in cols], show="headings", height=height, selectmode="browse")
    _TREES.append(tr)
    tr.bind("<Destroy>", lambda e, t=tr: _TREES.remove(t) if e.widget is t and t in _TREES else None, add="+")
    for cid, head, w, anc in cols:
        tr.heading(cid, text=head, anchor=anc)
        tr.column(cid, width=int(w * K), minwidth=int(40 * K), anchor=anc, stretch=True)
    ys = ttk.Scrollbar(fr, orient="vertical", command=tr.yview)
    tr.configure(yscrollcommand=ys.set)
    if xscroll:
        xs = ttk.Scrollbar(fr, orient="horizontal", command=tr.xview)
        tr.configure(xscrollcommand=xs.set)
        xs.pack(side="bottom", fill="x")
    ys.pack(side="right", fill="y")
    tr.pack(side="left", fill="both", expand=True)
    if not xscroll:
        tot = sum(c[2] for c in cols)

        def fit(_=None):
            W = tr.winfo_width() - 6
            if W > 60:
                for cid, _h, w, _a in cols:
                    tr.column(cid, width=max(int(34 * K), int(W * w / tot)))
        tr.bind("<Configure>", fit)
    tree_tags(tr)
    return fr, tr

def fill(tree, rows):
    tree.delete(*tree.get_children())
    for i, (iid, vals, tags) in enumerate(rows):
        tree.insert("", "end", iid=iid, values=vals, tags=tuple(tags) + (("odd",) if i % 2 else ()))

# --------------------------------------------------------------------------- application
class App(tk.Frame):
    def __init__(self, master=None, embedded=False, close_callback=None, office_id=None):
        if master is None:
            master = tk.Tk()
        super().__init__(master)
        self.window = master
        self.embedded = embedded
        self.close_callback = close_callback
        self._closed = False
        self._previous_theme = None
        self.core = Core(DB_FILE, OLD_JSON, check=True)
        self._stale = set()
        self._tabmap = {}
        self._syncing_code = False
        self._syncing_rep_code = False
        requested_office = office_id or os.environ.get("FEEBOOK_SAP_OFFICE_ID")
        if requested_office and any(o["id"] == requested_office for o in self.db["offices"]):
            self.db["cur"] = requested_office
            self.core.save()
        if embedded:
            style = ttk.Style(self.window)
            self._previous_theme = style.theme_use()
            self.style_theme = "smart_account_pro_embedded"
            if self.style_theme not in style.theme_names():
                style.theme_create(self.style_theme, parent=self._previous_theme)
            style.theme_use(self.style_theme)
        else:
            self.window.title("Smart Account Pro")
            set_icon(self.window)
            self.window.report_callback_exception = self.report_callback_exception
            self.auto_fit()
        self._deb = {}
        self.edit = None
        self.last = None
        self.rp = {"type": "account", "from": "", "to": "", "aid": "", "name_filter": ""}
        self.cur_day = today()
        self._toast_job = None
        self._tick_job = None
        self.cards = []
        self.hdr_w = []
        self.style = ttk.Style(self.window)
        if "clam" in self.style.theme_names():
            if not embedded:
                self.style.theme_use("clam")
        self.build_header()
        self.build_status()
        self.build_tabs()
        self.apply_theme()
        if not embedded:
            self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.cleanup_reports()
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.auto_backup(skip_existing=True)
        self.refresh_all()
        self.tick()

    @property
    def db(self):
        return self.core.db

    def auto_fit(self):
        global K
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        base = float(self.tk.call("tk", "scaling"))
        dpi = base / (96 / 72)
        lw, lh = sw / dpi, sh / dpi
        sc = max(0.85, min(1.3, min(lw / 1600, lh / 900)))
        self.tk.call("tk", "scaling", base * sc)
        K = dpi * sc
        w = min(int(sw * 0.92), int(max(1400 * K, sw * 0.70)))
        h = min(int(sh * 0.90), int(max(860 * K, sh * 0.75)))
        self.window.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 3)}")
        self.window.minsize(min(int(700 * K), sw - 40), min(int(460 * K), sh - 80))
        if lw < 1100 or lh < 680:
            try:
                self.window.state("zoomed")
            except tk.TclError:
                try:
                    self.window.attributes("-zoomed", True)
                except tk.TclError:
                    pass
        self._clk_on = True
        self.bind("<Configure>", self.on_resize)

    def on_resize(self, e):
        if e.widget is not self or not hasattr(self, "clk"):
            return
        show = e.width >= int(820 * K)
        if show != self._clk_on:
            self._clk_on = show
            if show:
                self.clk.pack(side="right", padx=10)
            else:
                self.clk.pack_forget()

    def deb(self, key, fn, ms=150):
        if key in self._deb:
            self.after_cancel(self._deb[key])
        self._deb[key] = self.after(ms, fn)

    def build_header(self):
        h = tk.Frame(self)
        h.pack(fill="x")
        self.hdr_w = [h]
        self.logo_img = load_logo_image(34)
        if self.logo_img:
            tk.Label(h, image=self.logo_img, bg="white", padx=3, pady=3).pack(side="left", padx=(12, 8), pady=6)
        ttl = tk.Label(h, text="Smart Account Pro", fg="white", font=("Segoe UI", 15, "bold"))
        ttl.pack(side="left", pady=6, padx=(0 if self.logo_img else 14, 0))
        self.osel = ttk.Combobox(h, state="readonly", width=24)
        self.osel.pack(side="right", padx=12)
        self.osel.bind("<<ComboboxSelected>>", self.on_office)
        self.clk = tk.Label(h, justify="right", fg="white", font=("Segoe UI", 9))
        self.clk.pack(side="right", padx=10)
        if self.embedded:
            ttk.Button(
                h, text="✕ बंद करें", command=self.on_close,
                style="Danger.TButton"
            ).pack(side="right", padx=8)
        self.hdr_w += [ttl, self.clk]
        self.stripe = tk.Frame(self, height=3, bg=GOLD)
        self.stripe.pack(fill="x")

    def build_status(self):
        self.sbar = tk.Label(self, anchor="w", bd=0, padx=10, pady=3, fg="white", font=("Segoe UI", 9))
        self.sbar.pack(side="bottom", fill="x")

    def build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.t_dash, self.t_ent, self.t_acc, self.t_rep, self.t_set = [ttk.Frame(self.nb) for _ in range(5)]
        for fr, txt in ((self.t_dash, "  ▦ डैशबोर्ड  "), (self.t_ent, "  ＋ एंट्री  "), (self.t_acc, "  ☰ खाते  "),
                        (self.t_rep, "  ▤ रिपोर्ट  "), (self.t_set, "  ⚙ सेटिंग  ")):
            self.nb.add(fr, text=txt)
        self._tabmap = {"dash": self.t_dash, "ent": self.t_ent, "acc": self.t_acc, "rep": self.t_rep, "set": self.t_set}
        self.build_dash()
        self.build_entry()
        self.build_acc()
        self.build_rep()
        self.build_set()
        self.nb.bind("<<NotebookTabChanged>>", self.refresh_visible)

    def apply_theme(self):
        acc = THEMES.get(self.db.get("theme", ""), THEMES[""])[0]
        dark, tint = mix(acc, "#000000", 0.30), mix(acc, "#ffffff", 0.84)
        soft, bg, edge = mix(acc, "#ffffff", 0.94), mix(acc, "#ffffff", 0.95), mix(acc, "#ffffff", 0.60)
        PAL.update(acc=acc, dark=dark, tint=tint, soft=soft, bg=bg)
        st = self.style
        self.configure(bg=bg)
        st.configure(".", background=bg, foreground=INK, font=("Segoe UI", 10), bordercolor=edge, focuscolor=bg, troughcolor=tint)
        st.configure("TLabelframe", background=bg, bordercolor=edge, relief="solid", borderwidth=1)
        st.configure("TLabelframe.Label", background=bg, foreground=dark, font=("Segoe UI", 10, "bold"))
        st.configure("Sec.TLabel", background=bg, foreground=dark, font=("Segoe UI", 11, "bold"))
        st.configure("TButton", background=acc, foreground="white", bordercolor=acc, lightcolor=acc, darkcolor=acc,
                     focuscolor=acc, relief="flat", padding=(12, 5), font=("Segoe UI", 10, "bold"))
        st.map("TButton", background=[("disabled", "#c8c8c8"), ("pressed", dark), ("active", mix(acc, "#000000", 0.14))],
               foreground=[("disabled", "#888888")], bordercolor=[("active", dark)])
        for nm, col in (("Ok", CR_COL), ("Danger", "#c0392b")):
            st.configure(nm + ".TButton", background=col, bordercolor=col, lightcolor=col, darkcolor=col, focuscolor=col)
            st.map(nm + ".TButton", background=[("pressed", mix(col, "#000000", 0.30)), ("active", mix(col, "#000000", 0.16))],
                   bordercolor=[("active", mix(col, "#000000", 0.30))])
        for nm, col in (("Cr", CR_COL), ("Dr", DR_COL)):
            st.configure(nm + ".TRadiobutton", foreground=col, font=("Segoe UI", 10, "bold"))
        for nm in ("TRadiobutton", "TCheckbutton"):
            st.configure(nm, background=bg)
            st.map(nm, background=[("active", bg)])
        st.configure("TEntry", fieldbackground="white", bordercolor=edge, padding=3)
        st.map("TEntry", bordercolor=[("focus", acc)])
        st.configure("TCombobox", fieldbackground="white", background=tint, arrowcolor=dark, bordercolor=edge, padding=3)
        st.map("TCombobox", fieldbackground=[("readonly", "white")], selectbackground=[("readonly", "white")],
               selectforeground=[("readonly", INK)], bordercolor=[("focus", acc)])
        st.configure("TNotebook", background=bg, borderwidth=0, tabmargins=(4, 6, 4, 0))
        st.configure("TNotebook.Tab", background=tint, foreground=dark, padding=(14, 7), borderwidth=0, font=("Segoe UI", 10, "bold"))
        st.map("TNotebook.Tab", background=[("selected", acc), ("active", mix(acc, "#ffffff", 0.65))],
               foreground=[("selected", "white")])
        st.configure("Treeview", rowheight=int(26 * K), font=("Segoe UI", 10), background="white", fieldbackground="white",
                     foreground=INK, bordercolor=edge, lightcolor="white", darkcolor="white")
        st.configure("Treeview.Heading", background=acc, foreground="white", relief="flat", padding=(6, 5), font=("Segoe UI", 9, "bold"))
        st.map("Treeview.Heading", background=[("active", dark)])
        st.map("Treeview", background=[("selected", acc)], foreground=[("selected", "white")])
        for o in ("Vertical", "Horizontal"):
            st.configure(f"{o}.TScrollbar", background=tint, troughcolor=bg, bordercolor=bg, arrowcolor=dark, lightcolor=tint, darkcolor=tint)
            st.map(f"{o}.TScrollbar", background=[("active", edge)])
        for w in self.hdr_w:
            w.configure(bg=acc)
        self.stripe.configure(bg=GOLD)
        self.sbar.configure(bg=dark)
        for fr, bar, lbls, tone in self.cards:
            col, bgc = {"c": (CR_COL, CR_BG), "d": (DR_COL, DR_BG)}.get(tone, (acc, tint))
            fr.configure(bg=bgc, highlightbackground=mix(col, "#ffffff", 0.60))
            bar.configure(bg=col)
            for lb in lbls:
                lb.configure(bg=bgc)
        for sf in ScrollFrame._all:
            sf.cv.configure(bg=bg)
        for tr in _TREES:
            try:
                tree_tags(tr)
            except tk.TclError:
                pass

    def toast(self, text):
        self.sbar.config(text=text)
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(2800, self.update_status)

    def update_status(self):
        self._toast_job = None
        o = self.core.office()
        self.sbar.config(text=f"✓ Ready   |   Office: {o['name'] if o else '—'}   |   खाते: {len(self.core.accs())}   |   एंट्री: {len(self.core.txs())} | Powerd By Shiv Computer")

    def info(self, text, kind="info", title="Smart Account Pro"):
        msgbox(self, title, text, kind)

    def ask(self, text):
        return confirm(self, "Smart Account Pro", text)

    def commit(self, msg=None):
        if not self.core.save():
            self.info("डेटा sap.db में सेव नहीं हो सका!\nDisk/File permission check karein.\n\n" + (self.core.err or ""), "error")
        elif msg:
            self.toast(msg)
        self.refresh_all()

    def tick(self):
        n = datetime.datetime.now()
        self.clk.config(text=f"{HD[n.weekday()]}, {n.strftime('%d-%m-%Y')}\n{n.strftime('%I:%M:%S %p')}")
        try:
            if self.core.refresh_external():
                self.refresh_all()
        except sqlite3.Error as exc:
            log_error(f"Could not refresh external accounting changes: {exc}")
            self.toast("⚠ Fee income refresh failed — see sap_error.log")
        if today() != self.cur_day:
            self.cur_day = today()
            self._stale = set(self._tabmap)
            self.refresh_visible()
        self._tick_job = self.after(1000, self.tick)

    def _cancel_jobs(self):
        for j in [self._tick_job, self._toast_job, *self._deb.values()]:
            if j:
                try:
                    self.after_cancel(j)
                except tk.TclError:
                    pass
        self._tick_job = self._toast_job = None
        self._deb.clear()

    def auto_backup(self, skip_existing=False):
        try:
            if not (self.db["offices"] or self.db["tx"]):
                return
            self.core.snapshot(os.path.join(os.path.dirname(os.path.abspath(DB_FILE)), "sap_auto_backup"),
                               f"sap_auto_{today()}", "sap_auto_", 14, skip_existing)
        except Exception:
            log_error("auto backup failed\n" + traceback.format_exc())

    def safety_copy(self, what):
        try:
            self.core.snapshot(os.path.join(os.path.dirname(os.path.abspath(DB_FILE)), "sap_auto_backup"),
                               f"sap_before_{what}_{datetime.datetime.now():%Y%m%d-%H%M%S}", "sap_before_", 10)
            return True
        except Exception as exc:
            details = "Safety backup failed\n" + traceback.format_exc()
            log_error(details)
            self.info(f"Safety backup nahi ban saka; koi data nahi hataya gaya.\n\n{exc}", "error")
            return False

    def _shutdown(self, notify=False):
        if self._closed:
            return True
        if not self.core.save():
            if notify:
                self.info("Data sap.db mein save nahi ho saka; application band nahi ki gayi.\n\n" + (self.core.err or ""), "error")
            return False
        self._closed = True
        self._cancel_jobs()
        self.auto_backup()
        self.core.close()
        self._stale.clear()
        self.cards.clear()
        self.hdr_w.clear()
        self._tabmap.clear()
        ScrollFrame._all.clear()
        _TREES.clear()
        _img_cache.clear()
        _uri_cache.clear()
        gc.collect()
        return True

    def _on_destroy(self, event):
        if event.widget is self:
            self._shutdown()

    def on_close(self):
        if self._closed:
            return
        if not self._shutdown(notify=True):
            return
        if self.embedded:
            if self._previous_theme:
                ttk.Style(self.window).theme_use(self._previous_theme)
            self.destroy()
            if self.close_callback:
                self.close_callback()
        else:
            self.window.destroy()

    def report_callback_exception(self, exc, val, tb):
        log_error("".join(traceback.format_exception(exc, val, tb)))
        try:
            self.toast("⚠ Kuch gadbad hui — byora sap_error.log mein hai")
        except Exception:
            pass

    def on_office(self, _=None):
        i = self.osel.current()
        if 0 <= i < len(self.db["offices"]):
            self.db["cur"] = self.db["offices"][i]["id"]
            self.edit = None
            self.commit()

    def refresh_all(self):
        O = self.db["offices"]
        self.osel["values"] = [o["name"] for o in O]
        cur = next((i for i, o in enumerate(O) if o["id"] == self.db["cur"]), -1)
        if cur >= 0:
            self.osel.current(cur)
        else:
            self.osel.set("")
        self._stale = set(self._tabmap)
        if not O and self.nb.select() != str(self.t_set):
            self.nb.select(self.t_set)
        self.refresh_visible()
        if not self._toast_job:
            self.update_status()

    def refresh_visible(self, _=None):
        if self._closed:
            return
        try:
            cur = self.nb.select()
        except tk.TclError:
            return
        run = {"dash": self.refresh_dash, "ent": lambda: (self.refresh_entry_form(), self.refresh_elist()),
               "acc": self.refresh_acc, "rep": self.refresh_report, "set": self.refresh_set}
        for k, fr in self._tabmap.items():
            if cur == str(fr) and k in self._stale:
                self._stale.discard(k)
                run[k]()

    # ---------------------------------------------------------------- dashboard
    def stat(self, parent, title, big=False, tone="n"):
        fr = tk.Frame(parent, bd=0, highlightthickness=1)
        bar = tk.Frame(fr, width=6)
        bar.pack(side="left", fill="y")
        body = tk.Frame(fr)
        body.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        t = tk.Label(body, text=title, anchor="w", fg=MUTED, font=("Segoe UI", 9, "bold"))
        v = tk.Label(body, text="—", anchor="w", fg={"c": CR_COL, "d": DR_COL}.get(tone, INK),
                     font=("Segoe UI", 20 if big else 15, "bold"))
        s = tk.Label(body, text="", anchor="w", fg=MUTED, font=("Segoe UI", 9))
        for w in (t, v, s):
            w.pack(fill="x")
        self.cards.append((fr, bar, (body, t, v, s), tone))
        parent.add(fr)
        return v, s

    def build_dash(self):
        sf = ScrollFrame(self.t_dash)
        sf.pack(fill="both", expand=True)
        f = sf.inner
        f.columnconfigure(0, weight=1)
        self.bk = ttk.Frame(f)
        self.bk.grid(row=0, column=0, sticky="ew")
        ttk.Label(self.bk, text="⚠ Backup 7 din se purana hai (ya liya nahi).", foreground="#b3402a").pack(side="left", padx=4, pady=4)
        ttk.Button(self.bk, text="Abhi Backup Lein", command=self.backup).pack(side="left")
        self.dv = {}
        hero = Flow(f, 300)
        hero.grid(row=1, column=0, sticky="ew")
        self.dv["rem"] = self.stat(hero, "🏦 Bachha Hua Balance (खर्च nikal kar)", True)
        self.dv["cnt"] = self.stat(hero, "🧾 Kul Entry / Khate", True)
        self.sec_m = ttk.Label(f, text="This Month", style="Sec.TLabel")
        self.sec_m.grid(row=2, column=0, sticky="w", padx=6, pady=(8, 0))
        mo = Flow(f, 230)
        mo.grid(row=3, column=0, sticky="ew")
        self.dv["mi"] = self.stat(mo, "💰 This Month आय (Income)", tone="c")
        self.dv["me"] = self.stat(mo, "💸 This Month खर्च (Expense)", tone="d")
        self.dv["mn"] = self.stat(mo, "📊 This Month Bachat (आय − खर्च)")
        self.sec_t = ttk.Label(f, style="Sec.TLabel")
        self.sec_t.grid(row=4, column=0, sticky="w", padx=6, pady=(8, 0))
        td = Flow(f, 230)
        td.grid(row=5, column=0, sticky="ew")
        self.dv["ti"] = self.stat(td, "💰 Today  ki आय (Income)", tone="c")
        self.dv["te"] = self.stat(td, "💸 Today  ka खर्च (Expense)", tone="d")
        self.dv["tn"] = self.stat(td, "💵 Today  ka Shesh (Cash in Hand)")
        mid = Flow(f, 430)
        mid.grid(row=6, column=0, sticky="ew")
        lf = ttk.LabelFrame(mid, text="Khate aur Balance", padding=6)
        fr, self.d_acc = make_tree(lf, [("c", "Code", 60, "center"), ("n", "Khata", 150, "w"), ("h", "Head", 90, "w"), ("k", "Prakar", 60, "w"), ("v", "Balance / खर्च (₹)", 120, "e")], 7)
        fr.pack(fill="both", expand=True)
        mid.add(lf)
        lf2 = ttk.LabelFrame(mid, text="Pichle 6 Mahine (हरा बार=आय / लाल बार =खर्च)", padding=6)
        self.cv = tk.Canvas(lf2, height=int(190 * K), bg="white", highlightthickness=1, highlightbackground="#adadad")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.draw_bars())
        mid.add(lf2)
        lf3 = ttk.LabelFrame(f, text="📅 आज की Entry ", padding=6)
        lf3.grid(row=7, column=0, sticky="ew", padx=4, pady=4)
        self.dq = tk.StringVar()
        self.dq.trace_add("write", lambda *a: self.deb("d", self.refresh_dlist))
        top = ttk.Frame(lf3)
        top.pack(fill="x")
        ttk.Label(top, text="🔍 Khojein:").pack(side="left")
        ttk.Entry(top, textvariable=self.dq).pack(side="left", fill="x", expand=True, padx=6)
        self.dh = ttk.Label(lf3, foreground="#5c6f69")
        self.dh.pack(anchor="w", pady=2)
        fr, self.d_ent = make_tree(lf3, self.ENT_COLS, 6)
        fr.pack(fill="both", expand=True)

    ENT_COLS = [("v", "#", 40, "w"), ("d", "Tareekh", 95, "w"), ("c", "Code", 60, "center"), ("a", "Khata", 125, "w"), ("he", "Head", 85, "w"), ("k", "Type", 50, "w"),
                ("n", "Vivaran", 200, "w"), ("cr", "Credit", 90, "e"), ("x", "Debit", 90, "e")]

    def ent_rows(self, rows):
        out = []
        for t in rows:
            k = self.core.kind_of(t["aid"])
            acc = self.core.acc(t["aid"])
            code = acc.get("code", "-") if acc else "-"
            head = acc.get("head", "") if acc else ""
            out.append((t["id"], (t.get("vno") or "", dmy(t["date"]), code, self.core.name(t["aid"]), head, KL[k], t.get("note", ""),
                                  fmt(t["amt"]) if t["type"] == "C" else "", fmt(t["amt"]) if t["type"] == "D" else ""), []))
        return out

    def refresh_dash(self):
        c, db = self.core, self.db
        A, T = c.by_kind(c.accs()), c.txs()
        mo = today()[:7]
        pm, pa, pt = c.pl(mo + "-01", mo + "-31"), c.pl(), c.pl(today(), today())
        tot = c.remaining()
        clr = lambda lbl, v: lbl.config(foreground=CR_COL if v >= 0 else DR_COL)
        self.dv["rem"][0].config(text=f"₹ {fmt(tot)}")
        clr(self.dv["rem"][0], tot)
        self.dv["cnt"][0].config(text=f"{len(T)} / {len(A)}")
        for key, v, sub, kind in (("mi", pm["i"], pa["i"], "c"), ("me", pm["e"], pa["e"], "d"), ("mn", pm["n"], pa["n"], "n")):
            self.dv[key][0].config(text=f"₹ {fmt(v)}", foreground={"c": CR_COL, "d": DR_COL}.get(kind, CR_COL if v >= 0 else DR_COL))
            self.dv[key][1].config(text=f"Kul: ₹ {fmt(sub)}")
        for key, v, kind in (("ti", pt["i"], "c"), ("te", pt["e"], "d"), ("tn", pt["n"], "n")):
            self.dv[key][0].config(text=f"₹ {fmt(v)}", foreground={"c": CR_COL, "d": DR_COL}.get(kind, CR_COL if v >= 0 else DR_COL))
        self.sec_t.config(text=f"Today  · {dmy(today())} ({dn(today())})")
        if T and (not db.get("lastBk") or (datetime.date.today() - datetime.date.fromisoformat(db["lastBk"])).days > 7):
            self.bk.grid()
        else:
            self.bk.grid_remove()
        fill(self.d_acc, [(a["id"], (a.get("code", "-"), a["name"], a.get("head", "-"), KL[c.kd(a)], fmt(c.bal(a)) if c.kd(a) == "I" else "खर्च " + fmt(c.spent(a))),
                                     ["cr" if c.kd(a) == "I" and c.bal(a) >= 0 else "dr"]) for a in A])
        self.draw_bars()
        self.refresh_dlist()

    def refresh_dlist(self):
        rows, n, sr = self.core.last_tx(self.dq.get(), True)
        more = f"  (Pehli {MAXR} dikhayi gayi)" if len(rows) > MAXR else ""
        self.dh.config(text=(f"🔎 {n} parinam mile (Today )" if sr else (f"📅 Today  ki {n} entry" if n else "Today  koi entry nahi")) + more)
        fill(self.d_ent, self.ent_rows(rows[:MAXR]))

    def draw_bars(self):
        cv = self.cv
        cv.delete("all")
        c = self.core
        if not c.office():
            return
        n, vals = datetime.date.today(), []
        for i in range(5, -1, -1):
            y, m = n.year, n.month - i
            while m < 1:
                m += 12
                y -= 1
            k = f"{y}-{m:02d}"
            p = c.pl(k + "-01", k + "-31")
            vals.append((MS[m - 1], p["i"], p["e"]))
        mx = max([1] + [max(v[1], v[2]) for v in vals])
        W, H = max(cv.winfo_width(), 260), max(cv.winfo_height(), 120)
        rh, x0 = H / 6, int(50 * K)
        bh = max(4, rh * 0.26)
        bw = max(30, W - x0 - int(165 * K))
        for i, (lbl, inc, exp) in enumerate(vals):
            y0 = i * rh + rh * 0.16
            cv.create_text(6, y0 + bh, text=lbl, anchor="w", font=("Segoe UI", 9))
            cv.create_rectangle(x0, y0, x0 + max(2, max(0, inc) / mx * bw), y0 + bh, fill=CR_COL, width=0)
            cv.create_rectangle(x0, y0 + bh + 2, x0 + max(2, max(0, exp) / mx * bw), y0 + 2 * bh + 2, fill=DR_COL, width=0)
            cv.create_text(W - 6, y0 + bh, text=f"{fmt(inc)} / {fmt(exp)}", anchor="e", font=("Segoe UI", 8), fill="#5c6f69")

    # ---------------------------------------------------------------- entry tab
    def build_entry(self):
        sf = ScrollFrame(self.t_ent)
        sf.pack(fill="both", expand=True)
        t = sf.inner
        self.ef = ttk.LabelFrame(t, text="Nayi Entry", padding=10)
        self.ef.pack(fill="x", padx=8, pady=(8, 4))
        self.ef.columnconfigure(0, weight=1)
        ttk.Label(self.ef, text="💡 खर्च khate mein Debit entry = Naya खर्च (Bachha hua paisa ghatega).", foreground="#5c6f69").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.et = tk.StringVar(value="C")
        rf = ttk.Frame(self.ef)
        rf.grid(row=1, column=0, sticky="w", pady=4)
        ttk.Radiobutton(rf, text="Credit (Jama)", variable=self.et, value="C", style="Cr.TRadiobutton").pack(side="left", padx=(0, 16))
        ttk.Radiobutton(rf, text="Debit (Naame)", variable=self.et, value="D", style="Dr.TRadiobutton").pack(side="left")
        fl = Flow(self.ef, 190)
        fl.grid(row=2, column=0, sticky="ew")
        self.ecode = field(fl, "Khata Code", ttk.Entry)
        self.ea = field(fl, "Khata", ttk.Combobox, state="readonly")
        self.ed = field(fl, "Tareekh (DD-MM-YYYY)", ttk.Entry)
        self.em = field(fl, "Rashi ₹", ttk.Entry)
        self.en = field(fl, "Vivaran", ttk.Combobox)
        bf = ttk.Frame(self.ef)
        bf.grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Button(bf, text="💾 Save Karein", command=self.save_entry, style="Ok.TButton").pack(side="left")
        self.ecancel = ttk.Button(bf, text="Radd", command=self.cancel_edit)

        self.ecode.bind("<KeyRelease>", lambda e: self.on_entry_code_change())
        self.ecode.bind("<Return>", lambda e: self.em.focus_set())
        self.ea.bind("<<ComboboxSelected>>", self.on_entry_acc_select)

        for w in (self.ed, self.em, self.en):
            w.bind("<Return>", lambda e: self.save_entry())
        lf = ttk.LabelFrame(t, text="Entry Suchi", padding=8)
        lf.pack(fill="both", expand=True, padx=8, pady=4)
        top = ttk.Frame(lf)
        top.pack(fill="x")
        ttk.Label(top, text="🔍 Khojein:").pack(side="left")
        self.eq = tk.StringVar()
        self.eq.trace_add("write", lambda *a: self.deb("e", self.refresh_elist))
        ttk.Entry(top, textvariable=self.eq).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="✎ Correction", command=self.edit_selected).pack(side="left", padx=2)
        ttk.Button(top, text="🗑 Delete", command=self.delete_selected, style="Danger.TButton").pack(side="left", padx=2)
        self.eh = ttk.Label(lf, foreground="#5c6f69")
        self.eh.pack(anchor="w", pady=2)
        fr, self.e_tree = make_tree(lf, self.ENT_COLS, 10)
        fr.pack(fill="both", expand=True)
        self.e_tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.e_tree.bind("<Delete>", lambda e: self.delete_selected())

    def acc_choices(self):
        A = self.core.by_kind(self.core.accs())
        self.amap = {f"{'💰' if self.core.kd(a) == 'I' else '💸'} [{a.get('code', '-')}] {a['name']} ({a.get('head', '-')})": a["id"] for a in A}
        self.arev = {v: k for k, v in self.amap.items()}

    def on_entry_code_change(self, *args):
        if self._syncing_code:
            return
        code = self.ecode.get().strip()
        if not code:
            return
        acc = next((a for a in self.core.accs() if norm(a.get("code", "")) == norm(code)), None)
        if acc:
            self._syncing_code = True
            for label, aid in self.amap.items():
                if aid == acc["id"]:
                    self.ea.set(label)
                    self.auto_type()
                    break
            self._syncing_code = False

    def on_entry_acc_select(self, _=None):
        aid = self.amap.get(self.ea.get())
        if aid:
            acc = self.core.acc(aid)
            if acc and acc.get("code"):
                self._syncing_code = True
                self.ecode.delete(0, "end")
                self.ecode.insert(0, acc["code"])
                self._syncing_code = False
            self.auto_type()

    def refresh_entry_form(self):
        self.acc_choices()
        self.ea["values"] = list(self.amap)
        if self.ea.get() not in self.amap:
            self.ea.set(next(iter(self.amap), ""))
            if not self.edit:
                self.auto_type()
        aid = self.amap.get(self.ea.get())
        if aid and not self.ecode.get():
            acc = self.core.acc(aid)
            if acc and acc.get("code"):
                self._syncing_code = True
                self.ecode.delete(0, "end")
                self.ecode.insert(0, acc["code"])
                self._syncing_code = False
        notes, seen = [], set()
        for t in reversed(self.core.txs()):
            n = t.get("note", "")
            if n and n not in seen:
                seen.add(n)
                notes.append(n)
                if len(notes) >= 50:
                    break
        self.en["values"] = notes
        if not self.ed.get() and not self.edit:
            self.ed.insert(0, dmy(today()))

    def auto_type(self, _=None):
        if self.edit:
            return
        aid = self.amap.get(self.ea.get())
        if aid:
            self.et.set("C" if self.core.kind_of(aid) == "I" else "D")

    def reset_form(self):
        self.edit = None
        self.ef.config(text="Nayi Entry")
        self.ecancel.pack_forget()
        for w in (self.ecode, self.ed, self.em):
            w.delete(0, "end")
        self.en.set("")
        self.ed.insert(0, dmy(today()))
        self.auto_type()
        aid = self.amap.get(self.ea.get())
        if aid:
            acc = self.core.acc(aid)
            if acc and acc.get("code"):
                self._syncing_code = True
                self.ecode.insert(0, acc["code"])
                self._syncing_code = False

    def cancel_edit(self):
        self.reset_form()

    def save_entry(self):
        c = self.core
        code_input = self.ecode.get().strip()
        if code_input:
            acc_by_c = next((a for a in c.accs() if norm(a.get("code", "")) == norm(code_input)), None)
            if acc_by_c:
                aid = acc_by_c["id"]
            else:
                return self.info(f"Account Code '{code_input}' ka koi khata nahi mila! Kripya sahi code chunein.", "warn")
        else:
            aid = self.amap.get(self.ea.get())

        date, amt, note = parse_date(self.ed.get()), parse_amt(self.em.get()), self.en.get().strip()
        account = c.acc(aid) if aid else None
        if not c.office() or not account or account["oid"] != self.db["cur"]:
            return self.info("Pehle khata chunein / banayein.", "warn")
        if not date or not amt or amt <= 0:
            return self.info("Khata, sahi tareekh (DD-MM-YYYY) aur sahi rashi bharein.", "warn")
        typ = self.et.get()
        if typ not in ("C", "D"):
            return self.info("Credit ya Debit ka sahi prakar chunein.", "warn")
        if self.edit:
            t = next((x for x in self.db["tx"] if x["id"] == self.edit), None)
            if t is None:
                self.reset_form()
                return self.info("Yeh entry ab maujud nahi hai.", "warn")
            t.update(aid=aid, type=typ, date=date, amt=amt, note=note)
        else:
            self.db["tx"].append({"id": uid(), "oid": self.db["cur"], "vno": c.next_v(), "aid": aid, "type": typ,
                                  "date": date, "amt": amt, "note": note})
        self.eq.set("")
        self.reset_form()
        self.commit("Save ho gaya")
        self.em.focus_set()

    def refresh_elist(self):
        rows, n, sr = self.core.last_tx(self.eq.get())
        tot = len({t.get("tid") or t["id"] for t in self.core.txs()})
        more = f"  (Pehli {MAXR} dikhayi gayi)" if len(rows) > MAXR else ""
        self.eh.config(text=(f"🔎 {n} parinam mile" if sr else (f"🕘 Navनवीन {min(GL, n)} entry · Kul {tot}" if n else "Abhi koi entry nahi")) + more)
        fill(self.e_tree, self.ent_rows(rows[:MAXR]))

    def sel(self, tree):
        s = tree.selection()
        return s[0] if s else None

    def edit_selected(self):
        tid = self.sel(self.e_tree)
        if not tid:
            return self.toast("Pehle suchi mein entry chunein")
        t = next((x for x in self.db["tx"] if x["id"] == tid), None)
        if not t:
            return
        if t.get("tid"):
            return self.info("Yeh purani Transfer entry hai — isko sudहराnahi ja sakta.", "warn")
        self.edit = tid
        self.ef.config(text="Entry Correction")
        self.acc_choices()
        self.ea.set(self.arev.get(t["aid"], ""))
        acc = self.core.acc(t["aid"])
        self._syncing_code = True
        self.ecode.delete(0, "end")
        if acc and acc.get("code"):
            self.ecode.insert(0, acc["code"])
        self._syncing_code = False
        self.et.set(t["type"])
        for w, v in ((self.ed, dmy(t["date"])), (self.em, numstr(t["amt"]))):
            w.delete(0, "end")
            w.insert(0, v)
        self.en.set(t.get("note", ""))
        self.ecancel.pack(side="left", padx=6)
        self.em.focus_set()

    def delete_selected(self):
        tid = self.sel(self.e_tree)
        if not tid:
            return self.toast("Pehle suchi mein entry chunein")
        t = next((x for x in self.db["tx"] if x["id"] == tid), None)
        if not t:
            return
        if t.get("tid"):
            related = [x for x in self.db["tx"] if x["oid"] == t["oid"] and x.get("tid") == t["tid"]]
            prompt = f"Yeh transfer aur iski {len(related)} judi entries Delete?"
        else:
            related = [t]
            prompt = "Yeh entry Delete?"
        if not self.ask(prompt):
            return
        remove_ids = {x["id"] for x in related}
        self.db["tx"] = [x for x in self.db["tx"] if x["id"] not in remove_ids]
        if self.edit == tid:
            self.reset_form()
        self.commit("Hata diya")

    # ---------------------------------------------------------------- accounts tab
    def build_acc(self):
        sf = ScrollFrame(self.t_acc)
        sf.pack(fill="both", expand=True)
        t = sf.inner
        lf = ttk.LabelFrame(t, text="Naya Khata & Head Option", padding=10)
        lf.pack(fill="x", padx=8, pady=(8, 4))
        lf.columnconfigure(0, weight=1)
        fl = Flow(lf, 180)
        fl.grid(row=0, column=0, sticky="ew")
        self.ac = field(fl, "Khata Code (Ex: 101)", ttk.Entry)
        self.an = field(fl, "Khate ka Naam (Ex: Petroll)", ttk.Entry)
        self.ak = field(fl, "Prakar (Income/Expense)", ttk.Combobox, state="readonly", values=["💸 खर्च (Expense)", "💰 आय (Income)"])
        self.ak.current(0)
        default_heads = ["Petroll", "Salary", "Stationery", "Rent", "Electricity", "Other", "Fees"]
        self.ah = field(fl, "Account Head (Head chunein ya type karein)", ttk.Combobox, values=default_heads)
        self.ao = field(fl, "Opening Balance ₹", ttk.Entry)

        btn_fr = ttk.Frame(lf)
        btn_fr.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Button(btn_fr, text="Add Account", command=self.add_acc).pack(side="left", padx=(0, 10))

        self.ac.bind("<Return>", lambda e: self.an.focus_set())
        self.an.bind("<Return>", lambda e: self.add_acc())
        self.ao.bind("<Return>", lambda e: self.add_acc())

        self.alf = ttk.LabelFrame(t, padding=8)
        self.alf.pack(fill="both", expand=True, padx=8, pady=4)
        bf = ttk.Frame(self.alf)
        bf.pack(fill="x", pady=(0, 6))
        ttk.Button(bf, text="✎ Correction (Edit Head/Name/Code)", command=self.edit_acc).pack(side="left", padx=2)
        ttk.Button(bf, text="⇄ आय/खर्च Badlein", command=self.toggle_kind).pack(side="left", padx=2)
        ttk.Button(bf, text="🗑 Delete", command=self.del_acc, style="Danger.TButton").pack(side="left", padx=2)
        fr, self.a_tree = make_tree(self.alf, [("c", "Code", 70, "center"), ("n", "Khata Naam", 180, "w"),
                                               ("hd", "Account Head", 120, "w"), ("k", "Prakar", 70, "w"),
                                               ("o", "Opening", 100, "e"), ("b", "Balance / खर्च", 120, "e")], 14)
        fr.pack(fill="both", expand=True)
        self.a_tree.bind("<Double-1>", lambda e: self.edit_acc())

    def next_suggested_code(self):
        codes = []
        for a in self.core.accs():
            c = a.get("code", "").strip()
            if c.isdigit():
                codes.append(int(c))
        return str(max(codes, default=100) + 1)

    def refresh_acc(self):
        c = self.core
        A = c.by_kind(c.accs())
        self.alf.config(text=f"Sabhi Khate ({len(A)})")
        fill(self.a_tree, [(a["id"], (a.get("code", "-"), a["name"], a.get("head", "-"), KL[c.kd(a)], fmt(a["open"]),
                                      fmt(c.bal(a)) if c.kd(a) == "I" else "खर्च " + fmt(c.spent(a))),
                            ["cr" if c.kd(a) == "I" else "dr"]) for a in A])
        heads = sorted(list({a.get("head", "Other") for a in c.accs() if a.get("head")}))
        if not heads:
            heads = ["Petroll", "Salary", "Stationery", "Other", "Fees"]
        self.ah["values"] = heads
        if not self.ac.get().strip():
            self.ac.delete(0, "end")
            self.ac.insert(0, self.next_suggested_code())

    def add_acc(self):
        c_val = self.ac.get().strip()
        n = self.an.get().strip()
        h = self.ah.get().strip() or "Other"
        if not self.core.office():
            return self.info("Pehle Settings mein Office banayein.", "warn")
        if not n:
            return self.info("Khate ka naam likhein.", "warn")
        if not c_val:
            c_val = self.next_suggested_code()
        if any(norm(a.get("code", "")) == norm(c_val) for a in self.core.accs()):
            return self.info(f"Account Code '{c_val}' pehle se maujud hai. Alag code chunein taaki mistake na ho.", "warn")
        if any(a["name"].casefold() == n.casefold() for a in self.core.accs()):
            return self.info("Yeh naam pehle se maujud hai.", "warn")
        o = parse_amt(self.ao.get() or "0")
        if o is None:
            return self.info("Opening Balance sahi likhein.", "warn")
        kind_val = "I" if self.ak.current() == 1 else "E"
        self.db["accounts"].append({"id": uid(), "oid": self.db["cur"], "name": n, "open": o,
                                    "kind": kind_val, "head": h, "code": c_val})
        self.ac.delete(0, "end")
        self.an.delete(0, "end")
        self.ao.delete(0, "end")
        self.commit("Khata jud gaya")

    def edit_acc(self):
        aid = self.sel(self.a_tree)
        a = self.core.acc(aid) if aid else None
        if not a:
            return self.toast("Select Account")
        r = form_dialog(self, "Edit Account", [
            ("text", "Khata Code (Account Code)", a.get("code", "")),
            ("text", "Khate ka Naam", a["name"]),
            ("text", "Account Head (Ex: Petroll/Salary)", a.get("head", "Other")),
            ("text", "Opening Balance", numstr(a["open"]))
        ])
        if r is None:
            return
        code_val = str(r[0]).strip() or a.get("code", "")
        nm, head_val, op = (str(r[1]).strip() or a["name"]), (str(r[2]).strip() or "Other"), parse_amt(r[3] or "0")
        if op is None:
            return self.info("Opening Balance sahi likhein.", "warn")
        if any(x["id"] != aid and norm(x.get("code", "")) == norm(code_val) for x in self.core.accs()):
            return self.info(f"Account Code '{code_val}' doosre khate mein pehle se hai.", "warn")
        if any(x["id"] != aid and x["name"].casefold() == nm.casefold() for x in self.core.accs()):
            return self.info("Yeh naam pehle se hai.", "warn")
        a["code"], a["name"], a["head"], a["open"] = code_val, nm, head_val, op
        self.commit("Success")

    def toggle_kind(self):
        aid = self.sel(self.a_tree)
        a = self.core.acc(aid) if aid else None
        if not a:
            return self.toast("Pehle khata chunein")
        a["kind"] = "E" if self.core.kd(a) == "I" else "I"
        self.commit(f"{a['name']} → {'आय (Income)' if a['kind'] == 'I' else 'व्यय (Expense)'}")

    def del_acc(self):
        aid = self.sel(self.a_tree)
        a = self.core.acc(aid) if aid else None
        if not a:
            return self.toast("Pehle khata chunein")
        cnt = [t for t in self.db["tx"] if t["aid"] == aid]
        transfer_ids = {t.get("tid") for t in cnt if t.get("tid")}
        related = [t for t in self.db["tx"] if t["oid"] == a["oid"] and
                   (t["aid"] == aid or t.get("tid") in transfer_ids)]
        extra = f"\n{len(related)} entries bhi hat jayengi." if related else ""
        if not self.ask(f'"{a["name"]}" Delete?{extra}'):
            return
        remove_ids = {t["id"] for t in related}
        self.db["tx"] = [t for t in self.db["tx"] if t["id"] not in remove_ids]
        self.db["accounts"] = [x for x in self.db["accounts"] if x["id"] != aid]
        self.commit("Khata hata diya")

    # ---------------------------------------------------------------- report tab
    def build_rep(self):
        sf = ScrollFrame(self.t_rep)
        sf.pack(fill="both", expand=True)
        t = sf.inner
        lf = ttk.LabelFrame(t, text="Report Options, Code & Name Filter", padding=10)
        lf.pack(fill="x", padx=8, pady=(8, 4))
        lf.columnconfigure(0, weight=1)
        fl = Flow(lf, 180)
        fl.grid(row=0, column=0, sticky="ew")
        self.rt = field(fl, "Report Prakar", ttk.Combobox, state="readonly", values=[x[1] for x in RT])
        self.rt.current(0)
        self.rcode = field(fl, "Khata Code (खाता कोड)", ttk.Entry)
        self.ra = field(fl, "Khata (खाता चुनें)", ttk.Combobox, state="readonly")
        self.rf = field(fl, "Se (DD-MM-YYYY)", ttk.Entry)
        self.rto = field(fl, "Tak (DD-MM-YYYY)", ttk.Entry)
        self.rname = field(fl, "Vivaran / Naam Filter", ttk.Entry)

        # Load Report Action Button
        btn_box = ttk.Frame(lf)
        btn_box.grid(row=1, column=0, sticky="w", pady=(8, 4))
        ttk.Button(btn_box, text="🔄 Load Report", command=self.load_report_action, style="Ok.TButton").pack(side="left", padx=(0, 10))

        self.rcode.bind("<KeyRelease>", lambda e: self.on_rep_code_change())
        self.ra.bind("<<ComboboxSelected>>", self.on_rep_acc_select)
        self.rt.bind("<<ComboboxSelected>>", lambda e: self.rpu())

        for w in (self.rf, self.rto, self.rname, self.rcode):
            w.bind("<Return>", lambda e: self.load_report_action())

        bf = Flow(lf, 150, "w")
        bf.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        for txt, cmd in (("This Month", lambda: self.quick("m")), ("Current Session", lambda: self.quick("y")), ("Sabhi Tareekh", lambda: self.quick("")),
                         ("🖨 Print / PDF", self.print_report), ("📊 Excel / CSV", self.export_csv), ("⚙ Page Setup", self.page_setup)):
            bf.add(ttk.Button(bf, text=txt, command=cmd))
        pv = ttk.LabelFrame(t, text="Preview", padding=8)
        pv.pack(fill="both", expand=True, padx=8, pady=4)
        self.rh = ttk.Label(pv, justify="center", anchor="center", font=("Segoe UI", 10))
        self.rh.pack(fill="x")
        fr, self.r_tree = make_tree(pv, [("x", "", 100, "w")], 12, xscroll=True)
        fr.pack(fill="both", expand=True)
        self.rn = ttk.Label(pv, foreground="#5c6f69", wraplength=600)
        self.rn.pack(anchor="w", pady=2)
        pv.bind("<Configure>", lambda e: self.rn.config(wraplength=max(200, e.width - 30)))

    def on_rep_code_change(self, *args):
        if self._syncing_rep_code:
            return
        code = self.rcode.get().strip()
        if not code:
            self._syncing_rep_code = True
            self.ra.set("Sabhi Khate")
            self.rp["aid"] = ""
            self._syncing_rep_code = False
            return
        acc = next((a for a in self.core.accs() if norm(a.get("code", "")) == norm(code)), None)
        if acc:
            self._syncing_rep_code = True
            for label, aid in self.rmap.items():
                if aid == acc["id"]:
                    self.ra.set(label)
                    self.rp["aid"] = acc["id"]
                    break
            self._syncing_rep_code = False

    def on_rep_acc_select(self, _=None):
        if self._syncing_rep_code:
            return
        aid = self.rmap.get(self.ra.get(), "")
        self.rp["aid"] = aid
        self._syncing_rep_code = True
        self.rcode.delete(0, "end")
        if aid:
            acc = self.core.acc(aid)
            if acc and acc.get("code"):
                self.rcode.insert(0, acc["code"])
        self._syncing_rep_code = False
        self.rpu()

    def refresh_report(self):
        A = self.core.accs()
        if self.rp["aid"] and not any(a["id"] == self.rp["aid"] for a in A):
            self.rp["aid"] = ""
        self.rmap = {"Sabhi Khate": ""}
        self.rmap.update({f"[{a.get('code', '-')}] {a['name']} ({a.get('head', '-')})": a["id"] for a in A})
        self.ra["values"] = list(self.rmap)
        cur_label = next((k for k, v in self.rmap.items() if v == self.rp["aid"]), "Sabhi Khate")
        self.ra.set(cur_label)
        if self.rp["aid"]:
            acc = self.core.acc(self.rp["aid"])
            if acc and acc.get("code"):
                self._syncing_rep_code = True
                self.rcode.delete(0, "end")
                self.rcode.insert(0, acc["code"])
                self._syncing_rep_code = False
        else:
            self._syncing_rep_code = True
            self.rcode.delete(0, "end")
            self._syncing_rep_code = False
        self.report()

    def rpu(self):
        rp = self.rp
        report_type = RT[self.rt.current()][0]
        f, t = parse_date(self.rf.get()), parse_date(self.rto.get())
        if f is None or t is None:
            self.toast("Tareekh DD-MM-YYYY mein likhein")
            return False
        if f and t and f > t:
            f, t = t, f
            self.toast("Tareekhein ulti thi, theek kar di gayi")
        rp["type"] = report_type
        rp["from"], rp["to"] = f, t
        for w, v in ((self.rf, f), (self.rto, t)):
            w.delete(0, "end")
            w.insert(0, dmy(v) if v else "")
        return True

    def load_report_action(self):
        code = self.rcode.get().strip()
        account = None
        if code:
            account = next((a for a in self.core.accs() if norm(a.get("code", "")) == norm(code)), None)
            if not account:
                return self.info(f"Account Code '{code}' ka koi khata nahi mila!\nKripya sahi code dalein taaki filter mein galti na ho.", "warn")
        if not self.rpu():
            return
        if account:
            self.rp["aid"] = account["id"]
            self._syncing_rep_code = True
            for label, aid in self.rmap.items():
                if aid == account["id"]:
                    self.ra.set(label)
                    break
            self._syncing_rep_code = False
        else:
            self.rp["aid"] = self.rmap.get(self.ra.get(), "")
        self.rp["name_filter"] = self.rname.get().strip()
        self.report()
        self.toast("Report load ho gayi!")

    def quick(self, k):
        d = datetime.date.today()
        if k == "m":
            self.rp["from"] = f"{d.year}-{d.month:02d}-01"
            self.rp["to"] = f"{d.year}-{d.month:02d}-{calendar.monthrange(d.year, d.month)[1]:02d}"
        elif k == "y":
            s = d.year if d.month > 3 else d.year - 1
            self.rp["from"], self.rp["to"] = f"{s}-04-01", f"{s + 1}-03-31"
        else:
            self.rp["from"] = self.rp["to"] = ""
        for w, v in ((self.rf, self.rp["from"]), (self.rto, self.rp["to"])):
            w.delete(0, "end")
            w.insert(0, dmy(v) if v else "")
        self.load_report_action()

    def report(self):
        if not self.core.office():
            self.last = None
            self.rh.config(text="Pehle Office banayein")
            fill(self.r_tree, [])
            return
        rep = self.last = self.core.report(self.rp)
        s = self.db.get("setup") or DS
        self.rh.config(text="\n".join(x for x in (rep.get("office"), rep.get("addr"), s.get("title"), rep.get("title"),
                                                  f"Avadhi: {rep.get('per', '')}   |   Khata: {rep.get('acc', '')}") if x))
        H, R, F = rep.get("H", []), rep.get("R", []), rep.get("F", [])
        tr = self.r_tree
        ids = [f"c{i}" for i in range(len(H))]
        tr.configure(columns=ids)
        for i, h in enumerate(H):
            num = isinstance(F[i], (int, float))
            tr.heading(ids[i], text=h, anchor="e" if num else "center" if h == "Code" else "w")
            w_col = 70 if h == "Code" else 260 if h == "विवरण" else 160 if h in ("खाता", "Avadhi", "Expense Head") else 110
            tr.column(ids[i], width=w_col, anchor="e" if num else "center" if h == "Code" else "w", stretch=True)
        tr.delete(*tr.get_children())
        for i, r in enumerate(R[:MAXPREV]):
            tr.insert("", "end", values=["" if c == "" else self.core.cell(c, j, F) for j, c in enumerate(r)], tags=("odd",) if i % 2 else ())
        tr.insert("", "end", values=["" if c == "" else self.core.cell(c, j, F) for j, c in enumerate(F)], tags=("foot",))
        extra = f"Preview mein pehli {MAXPREV} panktiyan (Kul {len(R)}) — Print / Excel mein poori report आयegi." if len(R) > MAXPREV else ""
        self.rn.config(text="\n".join(x for x in (rep["note"], extra) if x))

    @staticmethod
    def cleanup_reports(max_age=86400):
        now = time.time()
        for p in glob.glob(os.path.join(tempfile.gettempdir(), "SmartAccount_Report_*.html")):
            try:
                if now - os.path.getmtime(p) > max_age:
                    os.remove(p)
            except OSError:
                pass

    def print_report(self):
        if not self.last:
            return
        self.cleanup_reports()
        fd, path = tempfile.mkstemp(suffix=".html", prefix="SmartAccount_Report_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(self.core.report_html(self.last, logo_data_uri()))
        webbrowser.open(Path(path).as_uri())
        self.toast("Report browser mein khul gayi — Print / Save as PDF chunein")

    def export_csv(self):
        rep = self.last
        if not rep:
            return
        p = filedialog.asksaveasfilename(parent=self, title="CSV Save Karein", defaultextension=".csv",
                                         initialfile=f"Report_{self.rp['type']}_{today()}.csv", filetypes=[("CSV", "*.csv")])
        if not p:
            return

        def q(c):
            if isinstance(c, (int, float)) and not isinstance(c, bool):
                return f"{r2(c):.2f}"
            s = str(c)
            return "'" + s if s.lstrip(" \t\r\n\ufeff")[:1] in ("=", "+", "-", "@") else s

        rows = [[rep["office"]], [rep["title"]], ["Avadhi: " + rep["per"]], rep["H"], *rep["R"], rep["F"]]

        def write(f):
            w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
            for r in rows:
                w.writerow([q(c) for c in r])
        try:
            atomic_write(p, write, encoding="utf-8-sig", newline="")
            self.toast("CSV save ho gayi")
        except OSError as e:
            self.info(f"File save nahi ho saki:\n{e}", "error")

    def page_setup(self):
        s = self.db["setup"]
        r = form_dialog(self, "Page Setup", [
            ("choice", "Paper Size", s["paper"], list(PAPER)), ("choice", "Orientation", s["orient"], ["portrait", "landscape"]),
            ("text", "Top/Bottom Margin (mm)", s["mt"]), ("text", "Left/Right Margin (mm)", s["ml"]),
            ("text", "Font Size (px)", s["fs"]), ("text", "Extra Header Line", s["title"]),
            ("check", "Hastalakshar Line", s["sign"]), ("check", "Page Number", s["pn"])])
        if r is None:
            return

        def num(v, d, lo, hi):
            try:
                value = float(v)
                return min(hi, max(lo, value)) if math.isfinite(value) else d
            except (TypeError, ValueError, OverflowError):
                return d
        s.update(paper=r[0], orient=r[1], mt=num(r[2], 12, 0, 50), ml=num(r[3], 12, 0, 50), fs=num(r[4], 13, 8, 22),
                 title=r[5], sign=r[6], pn=r[7])
        self.commit("Page setup save hua")

    # ---------------------------------------------------------------- settings tab
    def build_set(self):
        sf = ScrollFrame(self.t_set)
        sf.pack(fill="both", expand=True)
        t = sf.inner
        lf = ttk.LabelFrame(t, text="Office", padding=10)
        lf.pack(fill="x", padx=8, pady=(8, 4))
        self.set_h = ttk.Label(lf, style="Sec.TLabel")
        self.set_h.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        lf.columnconfigure(0, weight=1)
        fl = Flow(lf, 240)
        fl.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.on = field(fl, "Office ka Naam", ttk.Entry)
        self.oa = field(fl, "Address / Phone (Vaikalpik)", ttk.Entry)
        ttk.Button(lf, text="Add Office", command=self.add_office).grid(row=2, column=0, sticky="w", pady=(6, 0))
        bf = ttk.Frame(lf)
        bf.grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 4))
        for txt, cmd in (("✔ Select", self.choose_office), ("✎ Correction", self.rename_office), ("🗑 Delete", self.del_office)):
            ttk.Button(bf, text=txt, command=cmd, style="Danger.TButton" if "Delete" in txt else "TButton").pack(side="left", padx=(0, 6))
        fr, self.o_tree = make_tree(lf, [("n", "Office", 280, "w"), ("a", "Address / Phone", 320, "w"), ("s", "Status", 90, "w")], 5)
        fr.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.o_tree.bind("<Double-1>", lambda e: self.choose_office())
        tf = ttk.LabelFrame(t, text="🎨 Theme Color", padding=10)
        tf.pack(fill="x", padx=8, pady=4)
        tfl = Flow(tf, 130, "w")
        tfl.pack(fill="x")
        for k, (col, lbl) in THEMES.items():
            tfl.add(tk.Button(tfl, text=lbl, bg=col, fg="white", activebackground=mix(col, "#000000", 0.2), activeforeground="white",
                              relief="flat", bd=0, padx=10, pady=6, cursor="hand2", font=("Segoe UI", 10, "bold"),
                              command=lambda k=k: self.set_theme(k)))
        bf2 = ttk.LabelFrame(t, text="Backup / Restore", padding=10)
        bf2.pack(fill="x", padx=8, pady=4)
        nl = ttk.Label(bf2, text="Data sap.db (SQLite) mein save rehta hai. Backup JSON aur DB dono mein liya ja sakta hai.",
                       foreground="#5c6f69", wraplength=600)
        nl.pack(fill="x")
        r = Flow(bf2, 170, "w")
        r.pack(fill="x", pady=6)
        for txt, cmd in (("⬇ Backup Save Karein", self.backup), ("⬆ Restore Karein", self.restore), ("🗑 Sara Data Mitayein", self.reset_all)):
            r.add(ttk.Button(r, text=txt, command=cmd, style="Danger.TButton" if "Mitayein" in txt else "TButton"))
        self.lbk = ttk.Label(bf2, foreground="#5c6f69")
        self.lbk.pack(anchor="w")
        dr = ttk.Frame(bf2)
        dr.pack(fill="x", pady=(6, 0))
        dl = ttk.Label(dr, text="📁 Data Folder: " + os.path.dirname(os.path.abspath(DB_FILE)), foreground="#5c6f69", wraplength=600)
        dl.pack(side="left", fill="x", expand=True)
        ttk.Button(dr, text="Open", command=self.open_data_dir).pack(side="right")

    def open_data_dir(self):
        folder = os.path.dirname(os.path.abspath(DB_FILE))
        try:
            if os.name == "nt":
                os.startfile(folder)
            else:
                webbrowser.open(Path(folder).as_uri())
        except Exception:
            self.info("Folder khola nahi ja saka:\n" + folder, "warn")

    def refresh_set(self):
        O = self.db["offices"]
        self.set_h.config(text="Office" if O else "Swagat hai! Pehla Office banayein")
        fill(self.o_tree, [(o["id"], (o["name"], o.get("addr") or "", "● Chalu" if o["id"] == self.db["cur"] else ""), []) for o in O])
        self.lbk.config(text=f"Pichla Backup: {dmy(self.db['lastBk'])}" if self.db.get("lastBk") else "")

    def add_office(self):
        n = self.on.get().strip()
        if not n:
            return self.info("Office ka naam likhein.", "warn")
        o = {"id": uid(), "name": n, "addr": self.oa.get().strip()}
        self.db["offices"].append(o)
        self.db["cur"] = o["id"]
        self.on.delete(0, "end")
        self.oa.delete(0, "end")
        self.core.mig()
        self.edit = None
        self.commit("Office jud gaya")
        self.nb.select(self.t_dash)

    def choose_office(self):
        oid = self.sel(self.o_tree)
        if oid:
            self.db["cur"] = oid
            self.edit = None
            self.commit()

    def rename_office(self):
        oid = self.sel(self.o_tree)
        o = next((x for x in self.db["offices"] if x["id"] == oid), None)
        if not o:
            return self.toast("Pehle office chunein")
        r = form_dialog(self, "Office Correction", [("text", "Office ka Naam", o["name"]), ("text", "Address / Phone", o.get("addr") or "")])
        if r:
            name, addr = str(r[0]), str(r[1])
            o["name"], o["addr"] = name.strip() or o["name"], addr.strip()
            self.commit("Sudhar ho gaya")

    def del_office(self):
        oid = self.sel(self.o_tree)
        o = next((x for x in self.db["offices"] if x["id"] == oid), None)
        if not o:
            return self.toast("Pehle office chunein")
        if not self.ask(f'"{o["name"]}" aur iske sabhi khate Delete?'):
            return
        if not self.safety_copy("office"):
            return
        db = self.db
        db["accounts"] = [a for a in db["accounts"] if a["oid"] != oid]
        db["tx"] = [t for t in db["tx"] if t["oid"] != oid]
        db["offices"] = [x for x in db["offices"] if x["id"] != oid]
        if db["cur"] == oid:
            db["cur"] = db["offices"][0]["id"] if db["offices"] else None
        self.edit = None
        self.commit("Office hata diya")

    def set_theme(self, k):
        self.db["theme"] = k
        self.apply_theme()
        self.commit()

    BK_FMT = ["JSON + DB Dono", "Sirf JSON", "Sirf DB (SQLite)"]

    def backup(self):
        r = form_dialog(self, "Backup", [("choice", "Backup Format", self.BK_FMT[0], self.BK_FMT)])
        if r is None:
            return
        selected = str(r[0])
        i = self.BK_FMT.index(selected)
        want_json, want_db = i in (0, 1), i in (0, 2)
        ext = ".db" if i == 2 else ".json"
        types = [("SQLite DB", "*.db")] if i == 2 else [("JSON", "*.json")]
        p = filedialog.asksaveasfilename(parent=self, title="Backup Save Karein", defaultextension=ext,
                                         initialfile=f"SmartAccount_Backup_{today()}{ext}", filetypes=types)
        if not p:
            return
        base = os.path.splitext(p)[0]
        live = os.path.normcase(os.path.abspath(DB_FILE))
        if want_db and os.path.normcase(os.path.abspath(base + ".db")) == live:
            return self.info("Backup ko chalu sap.db ke upar nahi likha ja sakta.", "error")
        backup_date = today()
        old_backup_date = self.db.get("lastBk")
        saved = []
        try:
            if not self.core.save():
                raise OSError(self.core.err or "sap.db mein save nahi ho saka")
            if want_json:
                backup_data = dict(self.db)
                backup_data["lastBk"] = backup_date
                atomic_write(base + ".json", lambda f: json.dump(backup_data, f, ensure_ascii=False, indent=1), encoding="utf-8")
                saved.append("JSON")
            if want_db:
                tmp = base + ".db.tmp"
                if os.path.exists(tmp):
                    os.remove(tmp)
                self.core.export_db(tmp)
                bc = sqlite3.connect(tmp)
                try:
                    with bc:
                        bc.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('lastBk',?)", (backup_date,))
                finally:
                    bc.close()
                os.replace(tmp, base + ".db")
                saved.append("DB")
        except (OSError, sqlite3.Error, TypeError, ValueError) as e:
            return self.info(f"Backup save nahi ho saka:\n{e}", "error")
        self.db["lastBk"] = backup_date
        if not self.core.save():
            self.db["lastBk"] = old_backup_date
            self.core._dirty()
            self.refresh_all()
            return self.info("Backup file ban gayi par lastBk save nahi hua.", "error")
        self.refresh_all()
        self.toast("Backup save ho gaya (" + " + ".join(saved) + ")")

    @staticmethod
    def load_backup(p):
        with open(p, "rb") as f:
            head = f.read(16)
        if head.startswith(b"SQLite format 3"):
            con = None
            try:
                try:
                    con = sqlite3.connect(Path(os.path.abspath(p)).as_uri() + "?mode=ro", uri=True)
                    con.execute("PRAGMA query_only=ON")
                    con.execute("SELECT 1 FROM sqlite_master LIMIT 1")
                except sqlite3.Error:
                    if con is not None:
                        con.close()
                    con = sqlite3.connect(p)
                    con.execute("PRAGMA query_only=ON")
                d = Core.read(con)
            finally:
                if con is not None:
                    con.close()
            return d
        with open(p, encoding="utf-8-sig") as f:
            d = json.load(f)
        if not isinstance(d, dict) or not all(isinstance(d.get(k), list) for k in ("offices", "accounts", "tx")):
            raise ValueError("not a backup")
        return d

    def restore(self):
        p = filedialog.askopenfilename(parent=self, title="Backup Chunein",
                                       filetypes=[("Backup (JSON / DB)", "*.json *.db"), ("All", "*.*")])
        if not p:
            return
        Core.skipped = 0
        try:
            d = self.load_backup(p)
        except (OSError, sqlite3.Error, UnicodeError, ValueError, TypeError, KeyError) as exc:
            log_error(f"Backup load failed: {p}\n{traceback.format_exc()}")
            return self.info(f"Backup file load nahi ho saki:\n{exc}", "error")
        if not self.ask("Maujuda data hat jayega aur backup se replace ho jayega. Jari rakhein?"):
            return
        c = Core.clean(d)
        skipped = Core.skipped
        if (d.get("offices") or d.get("tx")) and not c["offices"] and not c["tx"]:
            return self.info("Backup rows read nahi ho saki.", "error")
        if not self.safety_copy("restore"):
            return
        try:
            self.core.replace_all(c)
        except Exception as e:
            return self.info(f"Restore nahi ho saka.\n{e}", "error")
        self.edit = None
        self.apply_theme()
        self.commit("Restore pura hua")
        self.nb.select(self.t_dash)
        if skipped:
            self.info(f"Restore ho gaya, par {skipped} tootey records chhod diye gaye.", "warn")

    def reset_all(self):
        if not self.ask("Sara data mit jayega!"):
            return
        if not self.ask("Pakka? Yeh wapas nahi आयega."):
            return
        old = self.db
        if not self.safety_copy("reset"):
            return
        try:
            self.core.replace_all({"offices": [], "accounts": [], "tx": [], "cur": None, "setup": old["setup"], "theme": old.get("theme", "")})
        except Exception as e:
            return self.info(f"Data mitaya nahi ja saka:\n{e}", "error")
        self.edit = None
        self.commit("Sara data mita diya")

def main():
    if os.name == "nt":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    root = None
    try:
        root = tk.Tk()
        app = App(root)
        app.pack(fill="both", expand=True)
    except Exception as e:
        log_error(traceback.format_exc())
        try:
            error_root = root or tk.Tk()
            error_root.withdraw()
            messagebox.showerror(
                "Smart Account Pro",
                f"Program shuru nahi ho saka:\n{e}\n\nByora: sap_error.log",
                parent=error_root
            )
            error_root.destroy()
        except Exception:
            pass
        return
    root.mainloop()

if __name__ == "__main__":
    main()
