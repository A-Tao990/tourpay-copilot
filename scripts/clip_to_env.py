#!/usr/bin/env python3
"""Copy the current clipboard text into .env under KEY, WITHOUT printing it. Then clear the clipboard.
Usage: python3 scripts/clip_to_env.py PAYPAL_CLIENT_ID"""
import os, re, stat, sys
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

key = sys.argv[1]
if key not in ("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
    sys.exit("refusing unknown key name")
cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
got = []
cb.request_text(lambda c, t: (got.append(t), Gtk.main_quit()))
GLib.timeout_add(4000, Gtk.main_quit)
Gtk.main()
text = (got[0] if got and got[0] else "").strip()
if not re.fullmatch(r"[A-Za-z0-9_.\-]{10,200}", text):
    sys.exit("clipboard does not look like a credential (length %d); nothing written" % len(text))
path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
lines = open(path).read().splitlines() if os.path.exists(path) else []
out, done = [], False
for l in lines:
    if l.startswith(key + "="):
        out.append("%s=%s" % (key, text)); done = True
    else:
        out.append(l)
if not done: out.append("%s=%s" % (key, text))
open(path, "w").write("\n".join(out) + "\n"); os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
cb.set_text("", -1); cb.store()
print("stored %s (%d characters); clipboard cleared" % (key, len(text)))
