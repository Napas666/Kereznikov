"""
Kereznikov — CS 1.6 external hack
Aimbot работает через движение мыши (работает на ЛЮБОЙ сборке CS).
"""
import struct, math, threading, time
import pymem, pymem.process
import customtkinter as ctk
from tkinter import messagebox

# ── ОФФСЕТЫ build 8684 ───────────────────────────────────
ELIST  = 0x12043C8   # hw.dll entity list
ESIZE  = 0x250
ENAME  = 0x104
EPOS   = 0x188
VA     = 0x1230274   # hw.dll viewangles (только чтение — для определения угла)
ONGRND = 0x122E2D4   # hw.dll onground
FJUMP  = 0x131434    # client.dll force jump

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
    except: return (0., 0., 0.)

def ri(a):
    try: return pm.read_int(a)
    except: return 0

def wi(a, v):
    try: pm.write_int(a, v)
    except: pass

def rstr(a):
    try: return pm.read_bytes(a, 44).split(b'\x00')[0].decode('utf-8','ignore').strip()
    except: return ""

def get_angles(): return rv3(hw + VA)
def is_ground():  return ri(hw + ONGRND) == 1

def my_pos():
    return rv3(hw + ELIST + 1 * ESIZE + EPOS)

def get_bots():
    me = rstr(hw + ELIST + 1 * ESIZE + ENAME)
    out = []
    for i in range(1, 33):
        n = rstr(hw + ELIST + i * ESIZE + ENAME)
        if not n or n == me: continue
        p = rv3(hw + ELIST + i * ESIZE + EPOS)
        if p == (0.,0.,0.): continue
        out.append(p)
    return out

def norm(a):
    while a >  180: a -= 360
    while a < -180: a += 360
    return a

# ── ДВИЖЕНИЕ МЫШИ (работает на любой сборке) ─────────────
def move_mouse(dx, dy):
    """Двигаем мышь на dx/dy пикселей — CS сам читает и поворачивает вид."""
    try:
        import win32api, win32con
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
    except: pass

# ── СОСТОЯНИЕ ─────────────────────────────────────────────
S   = {'aim': False, 'bhop': False}
# pix_per_deg — сколько пикселей мыши = 1 градус поворота
# По умолчанию (sens=3.0, m_yaw=0.022): 1/0.066 ≈ 15.15
CFG = {'fov': 60., 'smooth': 3., 'pix_per_deg': 15.15, 'head': True}

# ── АВТО-КАЛИБРОВКА ЧУВСТВИТЕЛЬНОСТИ ────────────────────
def calibrate(result_label):
    """Двигает мышь вправо, измеряет угол, вычисляет pix_per_deg."""
    if not ok:
        result_label.configure(text="Сначала нажми ATTACH!", text_color="#f44")
        return

    def _run():
        PIXELS = 300  # двигаем на 300 px вправо
        result_label.configure(text="Жди 1 сек...", text_color="#fc8")
        time.sleep(1.0)

        yaw_before = get_angles()[1]
        move_mouse(PIXELS, 0)
        time.sleep(0.15)                      # ждём пока CS обработает ввод
        yaw_after = get_angles()[1]

        delta = norm(yaw_after - yaw_before)  # сколько градусов повернулись

        if abs(delta) < 0.5:
            result_label.configure(text="Не сработало — запусти CS и войди на карту", text_color="#f44")
            return

        ppd = PIXELS / abs(delta)             # пикселей на градус
        CFG['pix_per_deg'] = ppd

        # Двигаем мышь обратно чтобы вернуть вид
        move_mouse(-PIXELS, 0)

        result_label.configure(
            text=f"Готово! pix/deg={ppd:.2f}  (delta={delta:.1f}°)",
            text_color="#4f8"
        )

    threading.Thread(target=_run, daemon=True).start()

# ── AIMBOT ────────────────────────────────────────────────
def aim_loop():
    while True:
        if S['aim'] and ok:
            try:
                ca   = get_angles()      # текущие углы (для сравнения)
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
                    dp  = norm(best[0] - ca[0]) / CFG['smooth']
                    dy_ = norm(best[1] - ca[1]) / CFG['smooth']
                    ppd = CFG['pix_per_deg']
                    move_mouse(dy_ * ppd, -dp * ppd)
            except: pass
        time.sleep(0.008)

# ── BHOP (через память) ───────────────────────────────────
def bhop_loop():
    air = False
    while True:
        if S['bhop'] and ok:
            try:
                gnd = is_ground()
                if not gnd:
                    wi(cl + FJUMP, 5)
                    air = True
                elif air:
                    wi(cl + FJUMP, 0)
                    air = False
            except: pass
        time.sleep(0.005)

threading.Thread(target=aim_loop,  daemon=True).start()
threading.Thread(target=bhop_loop, daemon=True).start()

# ── UI ────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
AC="#c850ff"; BG="#0d0d0d"; C1="#161616"; C2="#1a1a1a"

root = ctk.CTk()
root.title("Kereznikov"); root.geometry("340x620")
root.resizable(False,False); root.configure(fg_color=BG)

# Шапка
hdr = ctk.CTkFrame(root, fg_color=C1, corner_radius=0, height=50)
hdr.pack(fill="x")
ctk.CTkLabel(hdr, text="KEREZNIKOV", font=("Arial",16,"bold"), text_color=AC).pack(side="left",padx=14,pady=12)
dot  = ctk.CTkLabel(hdr, text="●", font=("Arial",18), text_color="#f44"); dot.pack(side="right",padx=12)
slbl = ctk.CTkLabel(hdr, text="NOT ATTACHED", font=("Arial",10), text_color="#555"); slbl.pack(side="right")

def do_attach():
    res, msg = attach()
    if res:
        dot.configure(text_color="#4f8"); slbl.configure(text="ATTACHED")
    else:
        dot.configure(text_color="#f44"); slbl.configure(text=f"ERR:{msg[:20]}")

ctk.CTkButton(root, text="ATTACH TO CS 1.6", command=do_attach,
              fg_color="#1e1040", hover_color="#2e1860",
              border_color=AC, border_width=1,
              font=("Arial",12,"bold"), height=38,
              corner_radius=8).pack(fill="x",padx=14,pady=(12,4))

dbg = ctk.CTkLabel(root, text="p=--  y=--  bots=--",
                   font=("Courier",10), text_color="#444")
dbg.pack(pady=2)

# ── Тогглы ────────────────────────────────────────────────
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

make_btn("AIMBOT (мышь)",  "aim",  AC)
make_btn("BUNNY HOP",      "bhop", "#50ffaa")

# ── Слайдеры ─────────────────────────────────────────────
def slider_row(lbl, mn, mx, df, fmt, cb):
    f = ctk.CTkFrame(root, fg_color=C1, corner_radius=10); f.pack(fill="x",padx=14,pady=3)
    r = ctk.CTkFrame(f, fg_color="transparent"); r.pack(fill="x",padx=12,pady=(8,0))
    ctk.CTkLabel(r, text=lbl, font=("Arial",11), text_color="#aaa").pack(side="left")
    vl = ctk.CTkLabel(r, text=fmt(df), font=("Arial",11,"bold"), text_color=AC); vl.pack(side="right")
    def _cb(v): vl.configure(text=fmt(float(v))); cb(float(v))
    sl = ctk.CTkSlider(f, from_=mn, to=mx, command=_cb, button_color=AC, progress_color=AC)
    sl.set(df); sl.pack(fill="x",padx=12,pady=(4,10))

slider_row("FOV (градусы)", 5, 180, 60, lambda v:f"{int(v)}°", lambda v: CFG.update({'fov': v}))
slider_row("SMOOTH",       1,  15,  3, lambda v:f"{v:.1f}x",  lambda v: CFG.update({'smooth': v}))

# ── Калибровка ────────────────────────────────────────────
cal_f = ctk.CTkFrame(root, fg_color=C1, corner_radius=10); cal_f.pack(fill="x",padx=14,pady=3)
cal_r = ctk.CTkFrame(cal_f, fg_color="transparent"); cal_r.pack(fill="x",padx=12,pady=(10,4))
cal_lbl = ctk.CTkLabel(cal_r, text="pix/deg = 15.15  (не калиброван)",
                        font=("Courier",10), text_color="#555")
cal_lbl.pack(side="left")
ctk.CTkButton(cal_f, text="⚙  AUTO CALIBRATE SENSITIVITY",
              command=lambda: calibrate(cal_lbl),
              fg_color="#0d1a0d", hover_color="#143014",
              border_color="#44cc44", border_width=1,
              font=("Arial",11,"bold"), height=34,
              corner_radius=8).pack(fill="x",padx=12,pady=(0,10))

# Голова / Тело
tgt_f = ctk.CTkFrame(root, fg_color=C1, corner_radius=10); tgt_f.pack(fill="x",padx=14,pady=3)
tgt_r = ctk.CTkFrame(tgt_f, fg_color="transparent"); tgt_r.pack(fill="x",padx=12,pady=10)
ctk.CTkLabel(tgt_r, text="ЦЕЛЬ", font=("Arial",11), text_color="#aaa").pack(side="left")
tgt_btn = ctk.CTkSegmentedButton(tgt_r, values=["ГОЛОВА","ТЕЛО"],
    command=lambda v: CFG.update({'head': v=="ГОЛОВА"}),
    selected_color="#2a1040", unselected_color=C2, font=("Arial",11,"bold"))
tgt_btn.set("ГОЛОВА"); tgt_btn.pack(side="right")

# ── Тик UI ───────────────────────────────────────────────
def tick():
    if ok:
        try:
            p,y,_ = get_angles(); b = get_bots()
            st = " ► AIM" if S['aim'] and b else ""
            dbg.configure(text=f"p={p:.1f}  y={y:.1f}  bots={len(b)}{st}", text_color="#555")
        except: pass
    root.after(150, tick)

tick()
root.mainloop()
