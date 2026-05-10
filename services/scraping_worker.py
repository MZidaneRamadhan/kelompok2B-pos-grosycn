"""
services/scraping_worker.py
QThread worker — menjalankan scraping di background
agar UI PyQt6 tidak freeze saat request API berlangsung.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from controllers import supplier_controller
from services.places_service import PlacesAPIError


class ScrapingWorker(QThread):
    """
    Worker thread untuk proses scraping Google Places API.

    Signal:
        progress(int, str)  — persentase dan pesan status
        result_ready(list)  — list supplier hasil scraping
        error(str)          — pesan error jika gagal
    """
    progress     = pyqtSignal(int, str)
    result_ready = pyqtSignal(list)
    error        = pyqtSignal(str)

    def __init__(self, category: str, radius: int,
                 min_rating: float, parent=None):
        super().__init__(parent)
        self.category   = category
        self.radius     = radius
        self.min_rating = min_rating

    def run(self):
        """Dijalankan di thread terpisah saat .start() dipanggil."""
        try:
            self.progress.emit(10, f"Mempersiapkan pencarian '{self.category}'...")
            self.progress.emit(30, "Menghubungi Google Places API...")

            results = supplier_controller.scrape_and_save(
                self.category,
                self.radius,
                self.min_rating,
            )

            self.progress.emit(90, "Memproses hasil...")
            self.progress.emit(100, f"Selesai! {len(results)} supplier ditemukan.")
            self.result_ready.emit(results)

        except PlacesAPIError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Error tidak terduga:\n{str(e)}")
