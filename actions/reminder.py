"""Hatırlatıcı — Windows Görev Zamanlayıcı ile bildirim ayarlar."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _scripts_dir() -> Path:
    d = Path.home() / ".jarvis" / "reminders"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_script(task_name: str, message: str) -> Path:
    path = _scripts_dir() / f"{task_name}.py"
    msg_j = json.dumps(message)
    path.write_text(f"""
message = {msg_j}
try:
    from plyer import notification
    notification.notify(title="JARVIS Hatırlatıcı", message=message, timeout=15)
except Exception:
    try:
        import subprocess
        subprocess.run(["msg", "*", "/TIME:30", message], check=False)
    except Exception:
        pass
# Bip sesi kullanıcı isteğiyle kaldırıldı.
import pathlib; pathlib.Path(__file__).unlink(missing_ok=True)
""", encoding="utf-8")
    return path


def reminder(parameters: dict, **_) -> str:
    p        = parameters or {}
    date_str = p.get("date", p.get("tarih", "")).strip()
    time_str = p.get("time", p.get("saat", "")).strip()
    message  = p.get("message", p.get("mesaj", "Hatırlatıcı")).strip()

    if not date_str or not time_str:
        return "Efendim, tarih (YYYY-AA-GG) ve saat (SS:DD) bilgisi gerekiyor."

    try:
        target = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "Efendim, tarih YYYY-AA-GG ve saat SS:DD formatında olmalı."

    if target <= datetime.now():
        return "Efendim, geçmiş bir zamana hatırlatıcı ayarlayamam."

    task_name = f"JARVISHatirlatici_{target.strftime('%Y%m%d_%H%M%S')}"

    try:
        script = _write_script(task_name, message)
    except Exception as e:
        return f"Hatırlatıcı betiği oluşturulamadı: {e}"

    pythonw = Path(sys.executable).parent / "pythonw.exe"
    exe     = str(pythonw if pythonw.exists() else sys.executable)

    xml_path = _scripts_dir() / f"{task_name}.xml"
    xml_path.write_text(
        f'<?xml version="1.0" encoding="UTF-16"?>\n'
        f'<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
        f'<Triggers><TimeTrigger>'
        f'<StartBoundary>{target.strftime("%Y-%m-%dT%H:%M:%S")}</StartBoundary>'
        f'<Enabled>true</Enabled></TimeTrigger></Triggers>'
        f'<Actions><Exec><Command>{exe}</Command>'
        f'<Arguments>"{script}"</Arguments></Exec></Actions>'
        f'<Settings><StartWhenAvailable>true</StartWhenAvailable>'
        f'<ExecutionTimeLimit>PT2M</ExecutionTimeLimit><Enabled>true</Enabled></Settings>'
        f'</Task>',
        encoding="utf-16",
    )

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", str(xml_path), "/F"],
        capture_output=True, text=True,
    )
    xml_path.unlink(missing_ok=True)

    if result.returncode != 0:
        script.unlink(missing_ok=True)
        return f"Efendim, hatırlatıcı ayarlanamadı: {result.stderr.strip()}"

    friendly = target.strftime("%d %B %Y saat %H:%M")
    return f"Efendim, {friendly} için hatırlatıcı ayarlandı: '{message}'"
