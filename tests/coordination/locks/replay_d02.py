from pathlib import Path
from tempfile import TemporaryDirectory
import re, subprocess, sys
def main():
 root=Path(__file__).resolve().parents[3]
 for version in range(5):
  text=(root/f"tutorials/07-coordination/02-distributed-lock/v{version}/tutorial.md").read_text(); m=re.search(r"<!-- checkpoint: ([^ ]+) -->\n```python\n(.*?)\n```",text,re.S); assert m
  with TemporaryDirectory() as d:
   target=Path(d)/m.group(1); target.write_text(m.group(2)+"\n"); subprocess.run([sys.executable,str(target)],cwd=d,check=True)
  print(f"v{version} replay ok")
if __name__=="__main__": main()
