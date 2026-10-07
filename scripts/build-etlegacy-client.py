"""Combine the official Win64 archive and installed ET packs for LAN clients."""
import argparse,hashlib,json,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('template',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
assert hashlib.md5(args.archive.read_bytes()).hexdigest()=='89c36484778c9103542a1621b3df292d','Expected the official 2.86.0 Win64 archive'
manifest=json.loads((args.template/'lisp-install.json').read_text())
folder='etlegacy-v2.86.0-x64/'
args.output.parent.mkdir(parents=True,exist_ok=True)
temporary=args.output.with_suffix('.zip.partial')
with zipfile.ZipFile(args.archive) as source,zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as target:
    assert source.testzip() is None
    for entry in source.infolist():
        assert entry.filename.startswith(folder) and '..' not in Path(entry.filename).parts
        target.writestr(entry,source.read(entry))
    for name in ('pak0','pak1','pak2'):
        path=args.template/'etmain'/(name+'.pk3')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest['packSHA256']['etmain/'+name+'.pk3']
        target.write(path,folder+'etmain/'+name+'.pk3',compress_type=zipfile.ZIP_STORED)
    target.writestr(folder+'Start ET Legacy.bat','@echo off\r\ncd /d "%~dp0"\r\nstart "" "%~dp0etl.exe" +set fs_game legacy +set fs_homepath "%~dp0profile"\r\n')
    target.writestr(folder+'LAN-README.txt','''ET: Legacy 2.86.0 Windows x64 LAN client

Extract the whole ZIP to a writable folder. Run Start ET Legacy.bat.
Create your player profile. Choose a server at http://192.168.8.138/servers/.
Press ~ (or Shift+Esc) for the console and paste its connect command.
For a protected match, first enter: password YOUR_JOIN_PASSWORD
Example: connect 192.168.8.138:27015
Admin: rconpassword YOUR_ADMIN_PASSWORD, then rcon COMMAND.
Referee controls: ref YOUR_ADMIN_PASSWORD

Includes the official Windows release, its Legacy mod and original ET game packs.
Sources: https://www.etlegacy.com/download/file/765
https://mirror.etlegacy.com/etmain/
The original release's license, credits and installation notes are retained.
No account passwords or server credentials are included.
Game binaries and data are separate from the shareable LISP source project.
''')
with zipfile.ZipFile(temporary) as z:assert z.testzip() is None
temporary.replace(args.output)
print('PASS complete Windows LAN client ZIP:',args.output.stat().st_size,'bytes')
