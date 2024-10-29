import tkinter as tk
from tkinter import ttk, messagebox, font


import time
from queue import Queue

from datetime import datetime
from host_machine import RemoteDesktopPro
from ui_componants.constants import ConnectionStatus
from ui_componants.theme import Theme
from client_logic_seperated.handle_events import HandleEvents
class ExtendedFromRemoteDesktopPro(HandleEvents):
    
    def update_statistics(self):
        """Update session statistics"""
        if self.stats["start_time"]:
            duration = time.time() - self.stats["start_time"]
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)

            self.stats_labels["Duration"].configure(
                text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

            # Update other stats
            self.stats_labels["Data Transferred"].configure(
                text=f"{self.stats['bytes_sent'] / 1024:.1f} KB")
            self.stats_labels["Frames Captured"].configure(
                text=str(self.stats["frames_captured"]))
            self.stats_labels["Events Processed"].configure(
                text=str(self.stats["events_processed"]))

            if duration > 0:
                fps = self.stats["frames_captured"] / duration
                self.stats_labels["Average FPS"].configure(text=f"{fps:.1f}")

            quality = min(100, (fps * 10)) if fps > 0 else 0
            self.quality_bar["value"] = quality

    def on_closing(self):
        """Handle application closing"""
        if self.is_running:
            if messagebox.askokcancel("Quit", "Active session in progress. Do you want to quit?"):
                self.stop_session()
                self.root.destroy()
        else:
            self.root.destroy()
    
    
    
    
def main():
    """Main application entry point"""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    root = tk.Tk()
    app = ExtendedFromRemoteDesktopPro(root)
    root.mainloop()

if __name__ == "__main__":
    main()
