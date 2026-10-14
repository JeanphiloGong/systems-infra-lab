from pathlib import Path
from tempfile import TemporaryDirectory
import re, subprocess, sys

def main():
    root=Path(__file__).resolve().parents[3]
    for version in (6,7):
        text=(root/f"tutorials/01-storage-engines/05-lsm/v{version}/tutorial.md").read_text()
        match=re.search(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```",text,re.S)
        assert match
        with TemporaryDirectory() as directory:
            base=Path(directory); target=base/match.group(1); target.write_text(match.group(2)+"\n")
            subprocess.run([sys.executable,str(target)],cwd=base,check=True)
        print(f"v{version} replay ok")
if __name__=="__main__": main()
