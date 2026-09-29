"""Brief box for "keep + render" (Enter / PageDown over an image).

ask_render_brief() pops a small window with the kept image's thumbnail and
one multi-line box for a free-form brief ("she turns, laughs, teasing, says
'come here'"). Enter / PageDown = queue the render, Shift+Enter = new line,
Esc = keep only. It returns at once; on_submit(text) / on_cancel() do the
work, and fire at most once between them.
"""
import os
import tkinter as tk

BG = "#1e1e1e"
FG = "#e0e0e0"
DIM = "#9a9a9a"
BOX_BG = "#2a2a2a"
HINT = ("Enter = queue render   Shift+Enter = new line   "
        "Esc = keep only (no render)\n"
        "Undo (Ctrl+Z) moves the image back but does not cancel a queued "
        "render")


def ask_render_brief(parent, image_path, *, on_submit, on_cancel=None):
    top = tk.Toplevel(parent)
    top.title("Render with MiniMax H3")
    top.configure(bg=BG)
    top.transient(parent.winfo_toplevel())
    done = {"fired": False}

    def finish(callback, *args):
        if done["fired"]:
            return
        done["fired"] = True
        try:
            if callback is not None:
                callback(*args)
        except Exception as exc:
            print(f"[render_brief_dialog] callback failed: {exc}")
        finally:
            try:
                top.grab_release()
            except tk.TclError:
                pass
            top.destroy()

    def submit(event=None):
        finish(on_submit, text.get("1.0", "end-1c").strip())
        return "break"

    def cancel(event=None):
        finish(on_cancel)
        return "break"

    def newline(event=None):
        text.insert("insert", "\n")
        return "break"

    try:
        from PIL import Image, ImageTk

        with Image.open(image_path) as image:
            image.thumbnail((360, 360))
            top._thumb = ImageTk.PhotoImage(image)
        tk.Label(top, image=top._thumb, bg=BG).pack(padx=12, pady=(12, 4))
    except Exception:
        tk.Label(top, text="(preview unavailable)", bg=BG, fg=DIM).pack(
            padx=12, pady=(12, 4))

    tk.Label(top, text=os.path.basename(image_path), bg=BG, fg=DIM).pack()
    tk.Label(top, text="Brief (optional) - what happens, tone, who she is, "
                       "what she says. Blank = the frame decides.",
             bg=BG, fg=FG, wraplength=480, justify="left").pack(
        padx=12, pady=(8, 4), anchor="w")
    text = tk.Text(top, height=8, width=60, wrap="word", bg=BOX_BG, fg=FG,
                   insertbackground=FG, relief="flat", padx=6, pady=6)
    text.pack(padx=12, fill="both", expand=True)
    tk.Label(top, text=HINT, bg=BG, fg=DIM, justify="left").pack(
        padx=12, pady=(6, 4), anchor="w")

    buttons = tk.Frame(top, bg=BG)
    buttons.pack(padx=12, pady=(4, 12), anchor="e")
    tk.Button(buttons, text="Keep only", command=cancel).pack(
        side="right", padx=(6, 0))
    tk.Button(buttons, text="Queue render", command=submit).pack(side="right")

    for seq in ("<Return>", "<KP_Enter>", "<Next>"):
        text.bind(seq, submit)
    text.bind("<Shift-Return>", newline)
    top.bind("<Escape>", cancel)
    top.protocol("WM_DELETE_WINDOW", cancel)

    # Center over the parent window.
    top.update_idletasks()
    root = parent.winfo_toplevel()
    x = root.winfo_rootx() + (root.winfo_width() - top.winfo_reqwidth()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - top.winfo_reqheight()) // 2
    top.geometry(f"+{max(0, x)}+{max(0, y)}")
    try:
        top.grab_set()
    except tk.TclError:
        pass  # another grab is live; the dialog still works
    text.focus_set()
    return top


if __name__ == "__main__":
    import sys

    demo = tk.Tk()
    demo.withdraw()

    def show(value):
        print("submitted: " + repr(value))

    def quit_demo():
        print("keep only")

    dialog = ask_render_brief(demo, sys.argv[1], on_submit=show,
                              on_cancel=quit_demo)
    dialog.bind("<Destroy>", lambda e: e.widget is dialog and demo.quit())
    demo.mainloop()
