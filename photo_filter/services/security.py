from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
import threading
import time
from collections.abc import Callable

# Blacklist of reverse engineering, debugging, and memory dumping tools
_BLACKLISTED_TOOLS = {
    # Debuggers & Disassemblers
    "x64dbg.exe",
    "x32dbg.exe",
    "x96dbg.exe",
    "ida.exe",
    "ida64.exe",
    "idag.exe",
    "idag64.exe",
    "idaw.exe",
    "idaw64.exe",
    "ollydbg.exe",
    "windbg.exe",
    "radare2.exe",
    "cutter.exe",
    "ghidra.exe",
    # Memory search / Tampering
    "cheatengine.exe",
    "cheatengine-x86_64.exe",
    "cheatengine-x86_64-sse4-avx2.exe",
    "artmoney.exe",
    # Process Inspectors / Dumpers
    "processhacker.exe",
    "procexp.exe",
    "procexp64.exe",
    "scylla.exe",
    "scylla_x64.exe",
    "scylla_x86.exe",
    "pestudio.exe",
    "pe-bear.exe",
    "die.exe",  # Detect It Easy
    # .NET / Python Decompilers
    "dnspy.exe",
    "dnspy.console.exe",
    "ilspy.exe",
    "de4dot.exe",
    # Network / API Hooking
    "httpdebugger.exe",
    "httpdebuggerui.exe",
    "charles.exe",
    "fiddler.exe",
}

_watchdog_thread: threading.Thread | None = None
_stop_event = threading.Event()


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("cntUsage", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("cntThreads", ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def is_debugger_present() -> bool:
    """Check standard Win32 debugger presence APIs."""
    try:
        k32 = ctypes.windll.kernel32
        if k32.IsDebuggerPresent():
            return True

        is_remote = ctypes.c_bool(False)
        curr_proc = k32.GetCurrentProcess()
        if k32.CheckRemoteDebuggerPresent(curr_proc, ctypes.byref(is_remote)):
            if is_remote.value:
                return True
    except Exception:
        pass

    # Direct PEB check on x64 / x86
    try:
        ntdll = ctypes.windll.ntdll
        # NtQueryInformationProcess with ProcessDebugPort = 7
        debug_port = ctypes.c_ulong(0)
        status = ntdll.NtQueryInformationProcess(
            ctypes.windll.kernel32.GetCurrentProcess(),
            7,  # ProcessDebugPort
            ctypes.byref(debug_port),
            ctypes.sizeof(debug_port),
            None,
        )
        if status == 0 and debug_port.value != 0:
            return True
    except Exception:
        pass

    return False


def detect_blacklisted_processes() -> list[str]:
    """Fast scan of active process names to detect active reverse engineering tools."""
    detected: list[str] = []
    try:
        k32 = ctypes.windll.kernel32
        h_snapshot = k32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
        if h_snapshot == -1 or h_snapshot == 0xFFFFFFFFFFFFFFFF:
            return detected

        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)

        if k32.Process32FirstW(h_snapshot, ctypes.byref(entry)):
            while True:
                exe_name = entry.szExeFile.lower()
                if exe_name in _BLACKLISTED_TOOLS:
                    detected.append(exe_name)
                if not k32.Process32NextW(h_snapshot, ctypes.byref(entry)):
                    break

        k32.CloseHandle(h_snapshot)
    except Exception:
        pass

    return detected


def verify_security_environment() -> bool:
    """Run full initial anti-debug and anti-tamper check. Returns True if safe, False if compromised."""
    if is_debugger_present():
        return False

    bad_procs = detect_blacklisted_processes()
    if bad_procs:
        return False

    return True


def start_security_watchdog(on_breach: Callable[[], None] | None = None) -> None:
    """Start low-overhead background watchdog to guard against dynamic debugger attachment or tool launch."""
    global _watchdog_thread
    if _watchdog_thread and _watchdog_thread.is_alive():
        return

    _stop_event.clear()

    def _watchdog_loop() -> None:
        while not _stop_event.is_set():
            try:
                if is_debugger_present() or detect_blacklisted_processes():
                    if on_breach:
                        try:
                            on_breach()
                        except Exception:
                            pass
                    # Hard exit to prevent process dump or memory inspection
                    os._exit(0)
            except Exception:
                pass
            time.sleep(3.0)

    _watchdog_thread = threading.Thread(target=_watchdog_loop, name="KatiSecWatchdog", daemon=True)
    _watchdog_thread.start()


def stop_security_watchdog() -> None:
    """Signal watchdog thread to stop gracefully."""
    _stop_event.set()
