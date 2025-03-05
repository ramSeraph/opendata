from datetime import datetime, timedelta, UTC
from pathlib import Path
import sys

d = datetime.now(UTC).replace(day=1) - timedelta(days=1)
m = d.strftime('%b%Y')
Path(sys.argv[1]).write_text(m)
