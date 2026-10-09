#!/usr/bin/python3
from pathlib import Path
from html import escape
from urllib.parse import quote
import os

root = Path('/srv/lan-party')
tree = {'folders': {}, 'files': []}
total = count = 0
for p in sorted((root/'files').rglob('*'), key=lambda p: str(p).casefold()):
    rel = p.relative_to(root/'files')
    if not p.is_file() or p.is_symlink() or any(x.startswith('.') for x in rel.parts) or p.name.endswith(('.part','.filepart','.tmp')):
        continue
    size = p.stat().st_size
    total += size
    count += 1
    node = tree
    for folder in rel.parts[:-1]:
        node = node['folders'].setdefault(folder, {'folders': {}, 'files': []})
    node['files'].append((rel, size))

def size_label(n):
    return f'{n/1024**3:.2f} GB' if n>=1024**3 else f'{n/1024**2:.1f} MB'

def render(node):
    parts = ['<ul class="folder-list">']
    file_count = len(node['files'])
    for name, child in sorted(node['folders'].items(), key=lambda x:x[0].casefold()):
        contents, child_count = render(child)
        file_count += child_count
        parts.append(f'<li class="folder-node"><details class="download-folder"><summary><span class="folder-name">{escape(name)}</span></summary>{contents}</details></li>')
    for rel, size in node['files']:
        parts.append(f'<li class="download-file" data-search="{escape(rel.as_posix().casefold(),quote=True)}"><a download href="/files/{quote(rel.as_posix())}">{escape(rel.name)}</a><span class="file-size">{size_label(size)}</span></li>')
    parts.append('</ul>')
    return ''.join(parts), file_count

contents, _ = render(tree)
html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LAN Party Downloads</title><link rel="icon" type="image/png" href="/style/Coat%20of%20Arms.png"><link rel="stylesheet" href="/portal.css?v=20261009-account"></head><body><div class="downloads"><h1>LAN Party Downloads</h1><p>Open a folder to browse games, emulators and patches. Select a file to download it.</p>'''
html += '<label for="search">Find a download</label><input id="search" type="search" placeholder="Search filenames or folders…"><div class="button-row tree-controls"><button id="expand-folders" class="quiet" type="button">Expand all</button><button id="collapse-folders" class="quiet" type="button">Collapse all</button></div><div class="download-tree" aria-label="Download folders">'+contents+'</div>'
html += '''<p id="empty" hidden>No matching downloads.</p><footer>LAN access only. Download links refresh automatically after new files are uploaded.</footer><script>
(()=>{
 const scope=document.querySelector('.downloads');
 const folders=[...scope.querySelectorAll('.download-folder')];
 const files=[...scope.querySelectorAll('.download-file')];
 const expand=scope.querySelector('#expand-folders'),collapse=scope.querySelector('#collapse-folders');
 let saved=null;
 expand.onclick=()=>folders.forEach(x=>x.open=true);
 collapse.onclick=()=>folders.forEach(x=>x.open=false);
 scope.querySelector('#search').addEventListener('input',e=>{
  const q=e.target.value.trim().toLowerCase();
  if(q&&saved===null)saved=folders.map(x=>x.open);
  let matches=0;
  files.forEach(x=>{x.hidden=!!q&&!x.dataset.search.includes(q);if(!x.hidden)matches++});
  folders.forEach((x,i)=>{
   x.parentElement.hidden=!!q&&![...x.querySelectorAll('.download-file')].some(y=>!y.hidden);
   if(q)x.open=!x.parentElement.hidden;else if(saved!==null)x.open=saved[i];
  });
  if(!q)saved=null;
  expand.disabled=collapse.disabled=!!q;
  scope.querySelector('#empty').hidden=matches!==0;
 });
})();
</script></div><script src="/auth.js"></script><script src="/shell.js?v=20261009-account"></script></body></html>'''
tmp=root/'site/downloads/.index.html.tmp'
tmp.write_text(html,encoding='utf-8')
os.chmod(tmp,0o644)
tmp.replace(root/'site/downloads/index.html')
