#!/usr/bin/python3
"""Publish corresponding local Bracket source, without app secrets or build output."""
import pathlib,subprocess,sys,zipfile
root=pathlib.Path(__file__).resolve().parents[1];upstream=pathlib.Path(sys.argv[1]);destination=pathlib.Path(sys.argv[2]);destination.mkdir(parents=True,exist_ok=True)
assert subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()=='04d914157565683cda47e481c56c83b4b3051475'
files=subprocess.check_output(['git','-C',str(upstream),'ls-files','-z']).decode().split('\0')
with zipfile.ZipFile(destination/'Bracket-source.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in filter(None,files):
        p=upstream/name
        if p.is_file() and not p.is_symlink():z.write(p,'bracket/'+name)
    for name in ['scripts/patch-bracket-frontend.py','src/community.py','src/community_server.py','docs/licenses/Bracket-AGPL-3.0.txt','docs/COMMUNITY.md']:
        z.write(root/name,'lisp/'+name)
    z.writestr('REPRODUCE.md','Official Bracket commit 04d914157565683cda47e481c56c83b4b3051475, with local login/base-path/dark-theme modifications.\nFrontend source here is already patched. Use pnpm install --frozen-lockfile and pnpm run build. The provided patch sets the non-secret .env.production API URL. Backend: uv sync --locked --no-dev --python 3.12. See lisp/docs/COMMUNITY.md for local runtime configuration. Private credentials and database state are intentionally absent.\n')
with zipfile.ZipFile(destination/'Bracket-source.zip') as z:
    assert z.testzip() is None
    assert not any('/node_modules/' in n or '/.venv/' in n or '/dist/' in n or '/.git/' in n for n in z.namelist())
(destination/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Bracket source</title><link rel="stylesheet" href="/portal.css"><h1>Bracket source and licenses</h1><p>Official Bracket commit 04d914157565683cda47e481c56c83b4b3051475, with local login, URL and theme modifications. AGPL-3.0; copyright notices and license included.</p><p><a href="Bracket-source.zip">Download corresponding source and integration patch</a></p><p><a href="https://github.com/evroon/bracket/tree/04d914157565683cda47e481c56c83b4b3051475">Official pinned upstream source</a> · <a href="/tournaments/">Return to tournaments</a></p></html>',encoding='utf-8')
print('Corresponding Bracket source package created.')
