"""Final test to verify batch export dialog works correctly."""
import tkinter as tk
import time
import logging
from batch_export_dialog import BatchExportDialog

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    print("\n" + "="*60)
    print("BATCH EXPORT DIALOG - FINAL TEST")
    print("="*60)

    root = tk.Tk()
    root.withdraw()

    dialog = BatchExportDialog(root)

    # Wait for database to load (up to 30 seconds)
    print("\nWaiting for database to load...")
    for i in range(300):  # 30 seconds max
        time.sleep(0.1)
        root.update()  # Process events

        if dialog.db_loaded:
            break

        if i % 10 == 0:
            print(f"  Still loading... ({i/10:.0f}s)")

    # Check results
    if dialog.db_loaded:
        print("\n[SUCCESS] Database loaded!")

        # Check if tags are populated
        tag_count = len(dialog.tag_buttons)
        print(f"[INFO] Tag buttons created: {tag_count}")

        if tag_count > 0:
            print("[SUCCESS] Tags are displaying correctly!")
            print(f"[INFO] First 5 tags shown:")
            for i, (tag, btn) in enumerate(list(dialog.tag_buttons.items())[:5]):
                print(f"  - {tag}")
        else:
            print("[ERROR] No tag buttons created")

        # Test search functionality
        print("\n[TEST] Testing search functionality...")
        dialog.search_var.set("blowjob")
        root.update()
        time.sleep(0.5)
        root.update()

        filtered_count = len(dialog.tag_buttons)
        print(f"[INFO] Tags after search 'blowjob': {filtered_count}")

        if filtered_count > 0:
            print("[SUCCESS] Search is working!")
        else:
            print("[WARNING] No results for 'blowjob' search")

    else:
        print("\n[ERROR] Database failed to load after 30 seconds")

    dialog.destroy()
    root.destroy()

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == '__main__':
    main()