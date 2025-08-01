from datetime import datetime, timedelta, UTC
from pathlib import Path
import sys

out_file = sys.argv[1]
if len(sys.argv) != 3:
    months_back = 1
else:
    months_back = int(sys.argv[2])

d = datetime.now(UTC)
while months_back > 0:
    d = d.replace(day=1) - timedelta(days=1)
    months_back -= 1

m = d.strftime('%b%Y')
Path(out_file).write_text(m)
