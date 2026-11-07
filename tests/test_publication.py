import os
import threading

import pytest


@pytest.mark.skipif(os.name != 'nt', reason='Uses a real Windows directory sharing handle')
def test_publication_recovers_after_real_windows_sharing_lock(tmp_path, monkeypatch):
    import ctypes
    from ctypes import wintypes

    from genome.storage import publish_directory

    source, destination = tmp_path/'staging', tmp_path/'published'
    source.mkdir()
    (source/'genome.json').write_text('complete')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                   ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # GENERIC_READ includes directory-listing access, with shared reads/writes but
    # no FILE_SHARE_DELETE. Attribute-only access does not enforce this contention.
    handle = kernel.CreateFileW(str(source), 0x80000000, 0x3, None, 3, 0x02000000, None)
    assert handle != ctypes.c_void_p(-1).value, ctypes.get_last_error()
    released = threading.Event()
    failures = []
    actual_replace = os.replace

    def observed_replace(src, dst):
        try:
            actual_replace(src, dst)
        except OSError as exc:
            failures.append(exc.winerror)
            raise

    def release():
        kernel.CloseHandle(handle)
        released.set()

    monkeypatch.setattr('genome.storage.os.replace', observed_replace)
    timer = threading.Timer(.2, release)
    timer.start()
    try:
        publish_directory(source, destination)
    finally:
        timer.cancel()
        timer.join()
        if not released.is_set():
            release()
    assert failures and all(code in (5, 32, 33) for code in failures)
    assert not source.exists() and (destination/'genome.json').read_text() == 'complete'


@pytest.mark.parametrize('winerror,expected_attempts', [(5, 5), (32, 5), (33, 5), (112, 1)])
def test_publication_failure_remains_bounded(tmp_path, monkeypatch, winerror, expected_attempts):
    from genome.storage import publish_directory
    source = tmp_path/'staging'
    source.mkdir()
    calls = []
    sleeps = []

    def fail(*args):
        calls.append(args)
        error = OSError('simulated native error')
        error.winerror = winerror
        raise error

    monkeypatch.setattr('genome.storage.os.replace', fail)
    monkeypatch.setattr('genome.storage.time.sleep', sleeps.append)
    with pytest.raises(OSError, match='native error'):
        publish_directory(source, tmp_path/'published')
    assert len(calls) == expected_attempts
    assert sum(sleeps) <= 1
    assert source.exists() and not (tmp_path/'published').exists()
