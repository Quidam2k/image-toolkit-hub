"""Test the batch export dialog UI."""
import tkinter as tk
import logging
import time
from batch_export_dialog import BatchExportDialog

logging.basicConfig(level=logging.INFO)

def main():
    root = tk.Tk()
    root.title("Test Window")
    root.geometry("400x300")

    def open_dialog():
        print("\n=== Opening Batch Export Dialog ===")
        dialog = BatchExportDialog(root)

        # Schedule checks to see if it loaded
        def check_loaded(attempt=1):
            if attempt > 10:
                print(f"ERROR: Database not loaded after {attempt} attempts")
                return

            if dialog.db_loaded:
                tags = dialog.query_engine.list_available_tags()
                print(f"SUCCESS: Database loaded with {len(tags)} tags")

                # Check UI
                tag_buttons = len(dialog.tag_container.winfo_children())
                print(f"Tag buttons created: {tag_buttons}")

                if tag_buttons > 0:
                    print("SUCCESS: Tags are displaying in the UI!")
                else:
                    print("ERROR: Tags loaded but no buttons created")
            else:
                print(f"Attempt {attempt}: Database not loaded yet, checking again...")
                root.after(1000, lambda: check_loaded(attempt + 1))

        # Start checking after 1 second
        root.after(1000, check_loaded)

    # Add a button to open the dialog
    btn = tk.Button(root, text="Open Batch Export", command=open_dialog)
    btn.pack(expand=True)

    # Add info
    info = tk.Label(root, text="Click the button to test the batch export dialog")
    info.pack()

    # Auto-open after a short delay
    root.after(500, open_dialog)

    root.mainloop()

if __name__ == '__main__':
    main()
