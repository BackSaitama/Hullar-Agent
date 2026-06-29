"""
JARVIS İnternet Hız Testi (Skill 32).

speedtest-cli varsa gerçek ölçüm yapar; yoksa fast.com'u açar.
"""

import logging
import webbrowser

logger = logging.getLogger(__name__)


def hiz_testi(parameters: dict | None = None) -> str:
    """İnternet indirme/yükleme hızını ölçer."""
    try:
        import speedtest  # speedtest-cli
        st = speedtest.Speedtest()
        st.get_best_server()
        down = st.download() / 1_000_000   # Mbps
        up   = st.upload()   / 1_000_000
        ping = st.results.ping
        return (f"📶 İnternet Hızı:\n"
                f"⬇️ İndirme: {down:.1f} Mbps\n"
                f"⬆️ Yükleme: {up:.1f} Mbps\n"
                f"📡 Ping: {ping:.0f} ms")
    except ImportError:
        webbrowser.open("https://fast.com")
        return ("Efendim, hızlı ölçüm modülü kurulu değil; fast.com açıldı. "
                "Gerçek ölçüm için: pip install speedtest-cli")
    except Exception as exc:
        webbrowser.open("https://fast.com")
        return f"Efendim, ölçüm yapılamadı ({exc}); fast.com açıldı."
