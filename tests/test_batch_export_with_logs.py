"""Test batch export dialog with logging enabled."""
import tkinter as tk
import logging
from batch_export_dialog import BatchExportDialog

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

def main():
    print("\n" + "="*60)
    print("Testing Batch Export Dialog with Logging")
    print("="*60)
    print("\nOpening dialog... Watch the logs below:\n")

    root = tk.Tk()
    root.title("Test Window")
    root.geometry("300x200")
    root.withdraw()  # Hide the root window

    try:
        # Create dialog
        dialog = BatchExportDialog(root)

        print("\nDialog created. If tags don't appear after 10 seconds,")
        print("check the logs above for errors.\n")

        # Let it run
        root.mainloop()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
