"""Move the child into its delegated accounting cgroup before executing an engine."""
import os,sys
from pathlib import Path
group=Path(sys.argv[1]);expected=Path('/sys/fs/cgroup/system.slice/lan-portal.service')
if group.parent!=expected or not group.name.startswith('lisp-') or group.is_symlink():raise SystemExit('Invalid engine accounting group.')
(group/'cgroup.procs').write_text(str(os.getpid()))
os.execvpe(sys.argv[2],sys.argv[2:],os.environ)
