"""
Kereznikov — CS 1.6 aimbot через движение мыши
Работает на любой версии и любой мыши.
"""
import struct, math, threading, time
import pymem, pymem.process
import customtkinter as ctk

# ── ОФФСЕТЫ build 8684 ───────────────────────────────────
VA    = 0x1230274
ELIST = 0x12043C8
ESIZE = 0x250
ENAME = 0x104
EPOS  = 0x188
ONGRND= 0x122E2D4
FJUMP = 0x131434

# ── ПАМЯТЬ ────────────────────────────────────────────────
pm = None; hw = cl = 0; ok = False

def attach():
    global pm, hw, cl, ok
    try:
        pm = pymem.Pymem("cs.exe")
        hw = pymem.process.module_from_name(pm.process_handle, "hw.dll").lpBaseOfDll
        cl = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        ok = True; return True, "OK"
    except Exception as e:
        ok = False; return False, str(e)

def rv3(a):
    try: return struct.unpack('fff', pm.read_bytes(a, 12))
    except: return (0.,0.,0.)

def ri(a):
    try: return pm.read_int(a)
    except: return 0

def wi(a,v):
    try: pm.write_int(a, v)
    except: pass

def rstr(a):
    try: return pm.read_bytes(a,44).split(b'\x00')[0].decode('utf-8','ignore').strip()
    except: return ""

def get_angles(): return rv3(hw + VA)
def is_ground():  return ri(hw + ONGRND) == 1
def my_pos():     return rv3(hw + ELIST + ESIZE + EPOS)

def get_bots():
    me = rstr(hw + ELIST + ESIZE + ENAME)
    out = []
    for i in range(1, 33):
        n = rstr(hw + ELIST + i * ESIZE + ENAME)
        if not n or n == me: continue
        p = rv3(hw + ELIST + i * ESIZE + EPOS)
        if p != (0.,0.,0.): out.append(p)
    return out

def norm(a):
    while a >  180: a -= 360
    while a < -180: a += 360
    return a

def move_mouse(dx, dy):
    try:
        import win32api, win32con
        if abs(dx) > 0.5 or abs(dy) > 0.5:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
    except: pass

# ── СОСТОЯНИЕ ─────────────────────────────────────────────
S   = {'aim': False, 'bhop': False}
CFG = {'fov': 90., 'strength': 8., 'head': True}
# strength = пикселей мыши на градус разницы
# 8 = примерно для sens 3.0 в CS
# Если наводится медленно → увеличь
# Если дёргается → уменьши

# ── AIMBOT ────────────────────────────────────────────────
def aim_loop():
    while True:
        if S['aim'] and ok:
            try:
                ca   = get_angles()
                src  = my_pos()
                bots = get_bots()
                best = None; best_d = CFG['fov']

                for pos in bots:
                    tz = pos[2] + (64. if CFG['head'] else 0.)
                    dx,dy,dz = pos[0]-src[0], pos[1]-src[1], tz-src[2]
                    ta = (-math.degrees(math.atan2(dz, math.hypot(dx,dy))),
                           math.degrees(math.atan2(dy, dx)))
                    d = math.hypot(norm(ca[0]-ta[0]), norm(ca[1]-ta[1]))
                    if d < best_d: best_d, best = d, ta

                if best:
                    # Разница между нужным углом и текущим
                    dp  = norm(best[0] - ca[0])
                    dy_ = norm(best[1] - ca[1])
                    k   = CFG['strength']
                    # Клампим максимальный шаг чтобы не было рывков
                    mx  = 80.
                    px  = max(-mx, min(mx, dy_ * k))
                    py  = max(-mx, min(mx, -dp * k))
                    move_mouse(px, py)
            except: pass
        time.sleep(0.008)

# ── BHOP ──────────────────────────────────────────────────
def bhop_loop():
    air = False
    while True:
        if S['bhop'] and ok:
            try:
                gnd = is_ground()
                if not gnd: wi(cl + FJUMP, 5); air = True
                elif air:   wi(cl + FJUMP, 0); air = False
            except: pass
        time.sleep(0.005)

threading.Thread(target=aim_loop,  daemon=True).start()
threading.Thread(target=bhop_loop, daemon=True).start()

# ── UI ────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
AC="#c850ff"; BG="#0d0d0d"; C1="#161616"; C2="#1a1a1a"

root = ctk.CTk()
root.title("Kereznikov"); root.geometry("340x560")
root.resizable(False,False); root.configure(fg_color=BG)

hdr = ctk.CTkFrame(root, fg_color=C1, corner_radius=0, height=50)
hdr.pack(fill="x")
ctk.CTkLabel(hdr, text="KEREZNIKOV", font=("Arial",16,"bold"), text_color=AC).pack(side="left",padx=14,pady=12)
dot  = ctk.CTkLabel(hdr, text="●", font=("Arial",18), text_color="#f44"); dot.pack(side="right",padx=12)
slbl = ctk.CTkLabel(hdr, text="NOT ATTACHED", font=("Arial",10), text_color="#555"); slbl.pack(side="right")

def do_attach():
    ok2, msg = attach()
    if ok2: dot.configure(text_color="#4f8"); slbl.configure(text="ATTACHED")
    else:   dot.configure(text_color="#f44"); slbl.configure(text=f"ERR:{msg[:20]}")

ctk.CTkButton(root, text="ATTACH TO CS 1.6", command=do_attach,
              fg_color="#1e1040", hover_color="#2e1860",
              border_color=AC, border_width=1,
              font=("Arial",12,"bold"), height=38,
              corner_radius=8).pack(fill="x",padx=14,pady=(12,4))

dbg = ctk.CTkLabel(root, text="p=--  y=--  bots=--",
                   font=("Courier",10), text_color="#444")
dbg.pack(pady=2)

def make_btn(lbl, key, col):
    btn = ctk.CTkButton(root, text=f"◯  {lbl}  —  ВЫКЛ",
                        fg_color=C2, hover_color="#222",
                        border_color="#333", border_width=1,
                        font=("Arial",13,"bold"), height=48,
                        corner_radius=8, text_color="#555")
    def click():
        S[key] = not S[key]
        if S[key]: btn.configure(text=f"●  {lbl}  —  ВКЛ",  fg_color="#1e1040", border_color=col, text_color=col)
        else:      btn.configure(text=f"◯  {lbl}  —  ВЫКЛ", fg_color=C2, border_color="#333", text_color="#555")
    btn.configure(command=click)
    btn.pack(fill="x",padx=14,pady=4)

make_btn("AIMBOT", "aim",  AC)
make_btn("BHOP",   "bhop", "#50ffaa")

# ── Слайдеры ─────────────────────────────────────────────
def sld(lbl, hint, mn, mx, df, cb, fmt=lambda v:f"{v:.0f}"):
    f = ctk.CTkFrame(root, fg_color=C1, corner_radius=10); f.pack(fill="x",padx=14,pady=3)
    r = ctk.CTkFrame(f, fg_color="transparent"); r.pack(fill="x",padx=12,pady=(8,0))
    ctk.CTkLabel(r, text=lbl,  font=("Arial",11,"bold"), text_color="#ccc").pack(side="left")
    vl = ctk.CTkLabel(r, text=fmt(df), font=("Arial",11,"bold"), text_color=AC); vl.pack(side="right")
    ctk.CTkLabel(f, text=hint, font=("Arial",9), text_color="#444").pack(anchor="w",padx=12)
    def _cb(v): vl.configure(text=fmt(float(v))); cb(float(v))
    s = ctk.CTkSlider(f, from_=mn, to=mx, command=_cb, button_color=AC, progress_color=AC)
    s.set(df); s.pack(fill="x",padx=12,pady=(2,10))

sld("СИЛА АИМ", "Медленно ← 1 ——————— 30 → Быстро/рывки",
    1, 30, 8, lambda v: CFG.update({'strength': v}))

sld("FOV (зона захвата)", "Узко ← 5 ————————— 180 → Везде",
    5, 180, 90, lambda v: CFG.update({'fov': v}), lambda v:f"{int(v)}°")

# Голова / Тело
tf = ctk.CTkFrame(root, fg_color=C1, corner_radius=10); tf.pack(fill="x",padx=14,pady=3)
tr = ctk.CTkFrame(tf, fg_color="transparent"); tr.pack(fill="x",padx=12,pady=10)
ctk.CTkLabel(tr, text="ЦЕЛЬ", font=("Arial",11,"bold"), text_color="#ccc").pack(side="left")
tb = ctk.CTkSegmentedButton(tr, values=["ГОЛОВА","ТЕЛО"],
    command=lambda v: CFG.update({'head': v=="ГОЛОВА"}),
    selected_color="#2a1040", unselected_color=C2, font=("Arial",11,"bold"))
tb.set("ГОЛОВА"); tb.pack(side="right")

def tick():
    if ok:
        try:
            p,y,_ = get_angles(); b = get_bots()
            st = " ►AIM" if S['aim'] and b else ""
            dbg.configure(text=f"p={p:.1f} y={y:.1f} bots={len(b)}{st}", text_color="#555")
        except: pass
    root.after(150, tick)

tick()
root.mainloop()
