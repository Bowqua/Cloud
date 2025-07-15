import os, zipfile, pytest
from Cloud_backup.utils import retry, compress_path

def test_retry_success():
    calls = []
    @retry(max_attempts=3)
    def f(x):
        calls.append(x)
        return x*2
    assert f(3) == 6
    assert calls == [3]


def test_retry_failure():
    @retry(max_attempts=2)
    def g():
        raise ValueError
    with pytest.raises(ValueError):
        g()


def test_compress_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello")
    archive = compress_path(str(f))
    assert zipfile.ZipFile(archive).namelist() == ["a.txt"]
    os.remove(archive)


def test_compress_dir(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.txt").write_text("x")
    archive = compress_path(str(d))
    z = zipfile.ZipFile(archive)
    assert any(n.endswith("a.txt") for n in z.namelist())
    os.remove(archive)
