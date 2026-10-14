from pathlib import Path
from tempfile import TemporaryDirectory
import re, subprocess, sys

def main():
    root=Path(__file__).resolve().parents[3]
    for version in range(4):
        text=(root/f"tutorials/04-query/01-modeling/v{version}/tutorial.md").read_text()
        match=re.search(r"<!-- checkpoint: ([^ ]+) -->\n```python\n(.*?)\n```",text,re.S); assert match
        with TemporaryDirectory() as directory:
            target=Path(directory)/match.group(1); target.write_text(match.group(2)+"\n"); subprocess.run([sys.executable,str(target)],cwd=directory,check=True)
        print(f"v{version} replay ok")
if __name__=="__main__": main()
