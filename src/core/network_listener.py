import sys
import os
import threading
from PyQt6.QtCore import QObject, pyqtSignal

# Add sniffer directory to path to reach photon-packet-parser and market-decoder
import sys
from pathlib import Path

# Get the project root
ROOT = Path(__file__).resolve().parent.parent.parent
SNIFFER_PATH = ROOT / "sniffer"
sys.path.insert(0, str(SNIFFER_PATH))
sys.path.insert(0, str(SNIFFER_PATH / "photon-packet-parser"))

from photon_packet_parser import PhotonPacketParser
from market_decoder import MarketDecoder
import pydivert

class NetworkListener(QObject):
    """
    Фоновый слушатель сетевого трафика.
    Перехватывает пакеты Photon и декодирует рыночные данные.
    """
    # Сигналы для передачи данных в бот
    market_data_received = pyqtSignal(dict)  # {'type': 'search_results', 'data': [...]}
    request_detected = pyqtSignal(dict)      # {'filters': {...}}

    def __init__(self, port=5056):
        super().__init__()
        self.port = port
        self.parser = PhotonPacketParser(self.on_event, self.on_request, self.on_response)
        self._is_running = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self):
        with self._lock:
            self._is_running = False
            # Windivert will stop on context manager exit or we can let it time out

    def _run(self):
        """Основной цикл захвата пакетов"""
        try:
            filter_str = f"udp and (udp.SrcPort == {self.port} or udp.DstPort == {self.port})"
            with pydivert.WinDivert(filter_str, layer=pydivert.Layer.NETWORK, flags=pydivert.Flag.SNIFF) as w:
                for packet in w:
                    if not self._is_running:
                        break
                    try:
                        self.parser.HandlePayload(packet.payload)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[NetworkListener] Ошибка: {e}")
            self._is_running = False

    def on_event(self, payload):
        # Пока не используем события
        pass

    def on_request(self, payload):
        code = payload.operation_code
        params = payload.parameters
        
        # 1. Попытка декодировать запрос (категории/фильтры)
        decoded_req = MarketDecoder.decode_request(params)
        if decoded_req:
            self.request_detected.emit(decoded_req)
            return

        # 2. Попытка декодировать ответ (если направление перепутано)
        decoded_res = MarketDecoder.decode_response(params)
        if decoded_res:
            self.market_data_received.emit(decoded_res)

    def on_response(self, payload):
        code = payload.operation_code
        params = payload.parameters
        
        # Декодируем рыночный ответ
        decoded = MarketDecoder.decode_response(params)
        if decoded:
            self.market_data_received.emit(decoded)
