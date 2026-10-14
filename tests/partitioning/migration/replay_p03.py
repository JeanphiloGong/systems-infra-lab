from pathlib import Path
from tempfile import TemporaryDirectory
import re, subprocess, sys

def main():
    root=Path(__file__).resolve().parents[3]
    for version in range(5):
        text=(root/f"tutorials/03-partitioning-scaling/03-migration/v{version}/tutorial.md").read_text()
        code=re.search(r"<!-- checkpoint: ([^ ]+) -->\n\n```python\n(.*?)\n```",text,re.S)
        assert code
        with TemporaryDirectory() as directory:
            target=Path(directory)/code.group(1); target.write_text(code.group(2)+"\n")
            subprocess.run([sys.executable,str(target)],cwd=directory,check=True)
        print(f"v{version} replay ok")
if __name__=="__main__": main()
