import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from ctypes import windll

try:
    windll.shcore.SetProcessDpiAwareness(2) # Use 2 for per-monitor, 1 for system
except:
    pass # Fallback for non-Windows platforms


class AnnotationReviewer:

    def __init__(self, root):
        self.root = root
        self.root.title("ABSA Annotation Reviewer")
        self.root.geometry("1100x800")

        self.comments = []
        self.annotations = []

        self.comment_file = None
        self.json_file = None

        self.index = 0
        
        self.current_comment_index = 0
        self.current_annotation_index = 0


        # ---------------- Top buttons ----------------

        top = tk.Frame(root)
        top.pack(fill="x", padx=5, pady=5)

        tk.Button(
            top,
            text="Open Comments CSV",
            command=self.open_csv
        ).pack(side="left")

        tk.Button(
            top,
            text="Open JSON",
            command=self.open_json
        ).pack(side="left", padx=5)

        self.status = tk.Label(top, text="No files loaded")
        self.status.pack(side="right")

        # ---------------- Comment ----------------

        tk.Label(root, text="Comment").pack(anchor="w", padx=5)

        self.comment = ScrolledText(root, height=12, wrap="word")
        self.comment.pack(fill="both", expand=False, padx=5)

        # ---------------- JSON ----------------

        tk.Label(root, text="Annotation JSON").pack(anchor="w", padx=5)

        self.json = ScrolledText(root, height=12, wrap="none")
        self.json.pack(fill="both", expand=True, padx=5)

        # ---------------- Navigation ----------------

        nav = tk.Frame(root)
        nav.pack(fill="x", pady=5)

        tk.Button(
            nav,
            text="<< Previous",
            width=15,
            command=self.previous
        ).pack(side="left", padx=5)

        tk.Button(
            nav,
            text="Save && Next >>",
            width=15,
            command=self.next
        ).pack(side="left")

    # --------------------------------------------------

    def open_csv(self):

        filename = filedialog.askopenfilename(
            filetypes=[("CSV", "*.csv")]
        )

        if not filename:
            return

        self.comment_file = filename

        with open(filename, newline="", encoding="utf-8-sig") as f:
            self.comments = list(csv.DictReader(f))
        

        self.try_load()

    # --------------------------------------------------

    def open_json(self):

        filename = filedialog.askopenfilename(
            filetypes=[("JSONL", "*.jsonl")]
        )

        if not filename:
            return

        self.json_file = filename
        self.annotations = []

        with open(filename, newline="", encoding="utf-8-sig") as f:

            reader = csv.DictReader(f)

            for row in reader:
                self.annotations.append({
                    "i":row["i"],
                    "json":json.loads(row["json"])
                })
                
                
        print(self.annotations)
        
        self.current_annotation_index = 0;
        self.current_comment_index = int(self.annotations[0]["i"]);

        self.try_load()

    # --------------------------------------------------

    def try_load(self):

        if not self.comments or not self.annotations:
            return

        #if len(self.comments) != len(self.annotations):

        #    messagebox.showwarning(
        #        "Warning",
        #        f"CSV has {len(self.comments)} rows.\n"
        #        f"JSONL has {len(self.annotations)} rows."
        #    )

        self.index = self.current_comment_index
        self.show()

    # --------------------------------------------------

    def show(self):

        if not self.comments or not self.annotations:
            return

        self.status.config(
            text=f"Row {self.current_comment_index} / {len(self.comments)-1}"
        )

        row = self.comments[self.current_comment_index]

        self.comment.delete("1.0", tk.END)
        self.comment.insert("1.0", row["comment"])

        self.json.delete("1.0", tk.END)
        self.json.insert(
            "1.0",
            json.dumps(
                self.annotations[self.current_annotation_index]["json"],
                indent=4,
                ensure_ascii=False
            )
        )
        
        print(self.annotations[self.current_annotation_index]["json"])
        
        #if(self.annotations[self.current_annotation_index]["json"]["is_review"] == True):
        #    for ann in self.annotations[self.current_annotation_index]["json"]["annotations"]:
        #        self.auto_underline(ann["aspect_text"])
            
    # --------------------------------------------------
    
    def get_start_index(i):
        return self.annotations[0].i
        
        
    def get_annotation(comment_i):
        for i, ann in enumerate(self.annotations):
            if(self.annotations.i == comment_i):
                return ann
                

    
    # --------------------------------------------------

    def save_current(self):
        try:
            obj = json.loads(self.json.get("1.0", tk.END))
        except Exception as e:
            messagebox.showerror("Invalid JSON", str(e))
            return False

        saved_i = self.annotations[self.current_annotation_index]["i"]
        self.annotations[self.current_annotation_index] = {"i":saved_i, "json":obj}


        with open(self.json_file, "w", newline="", encoding="utf-8") as f:

            writer = csv.DictWriter(
                f,
                fieldnames=["i", "json"]
            )

            writer.writeheader()

            for ann in self.annotations:
                print(ann)
                writer.writerow({
                    "i": ann["i"],
                    "json": json.dumps(ann["json"], ensure_ascii=False, separators=(',',':'))
                })
                
                f.flush()

        return True

    # --------------------------------------------------

    def next(self):

        if not self.save_current():
            return
            
        if(self.current_annotation_index == len(self.annotations)-1):
            messagebox.showinfo("Info:", "Annotation complete")
            return

        if self.current_comment_index < len(self.comments) - 1:

            self.current_comment_index += 1
            self.current_annotation_index += 1
            self.show()

    # --------------------------------------------------

    def previous(self):

        if not self.save_current():
            return
            
        if(self.current_annotation_index == 0):
            messagebox.showinfo("Info:", "This is first annotation")
            return


        if self.current_comment_index > 0:

            self.current_comment_index -= 1
            self.current_annotation_index -= 1
            self.show()
        
        
        


root = tk.Tk()
AnnotationReviewer(root)
root.mainloop()