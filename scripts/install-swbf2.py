#!/usr/bin/python3
"""Extract the original v1.1 dedicated-server installer without running its GUI."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

def main():
    if os.geteuid()!=0:raise SystemExit('Run this installer with sudo.')
    source=Path(sys.argv[1]);root=Path(os.environ.get('LISP_SERVER_ROOT','/srv/lan-party/servers')).resolve()
    runtime=Path(os.environ.get('LISP_SWBF2_RUNTIME','/usr/share/steam/compatibilitytools.d/proton-cachyos-slr/files'))
    for tool in ('unshield','xvfb-run'): 
        if not shutil.which(tool):raise SystemExit('Install the dependency first: '+tool)
    if not (runtime/'share/default_pfx/system.reg').is_file():raise SystemExit('Install Proton CachyOS or set LISP_SWBF2_RUNTIME to its files directory.')
    with urllib.request.urlopen('http://127.0.0.1:8787/api/servers',timeout=3) as response:
        if json.load(response)['servers']:raise SystemExit('Stop running matches before installing or updating this template.')
    data=source.read_bytes()
    if hashlib.md5(data).hexdigest()!='7dff4d332505269810fd7313c44a944d':raise SystemExit('Installer checksum does not match the original ModDB v1.1 package.')
    templates=root/'templates';templates.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.swbf2-install-',dir=templates) as temp:
        stage=Path(temp)
        for name in ('data1.cab','data1.hdr','data2.cab'):
            needle=name.encode()+b'\0Disk1\\'+name.encode()+b'\0'
            start=data.index(needle)+len(needle);start=data.index(0,start)+1
            end=data.index(0,start);length=int(data[start:end]);start=end+1
            if data[start:start+4]!=b'ISc(' or start+length>len(data):raise SystemExit('Invalid InstallShield payload.')
            (stage/name).write_bytes(data[start:start+length])
        subprocess.run(['unshield','-d',str(stage/'unpacked'),'x',str(stage/'data1.cab')],check=True,stdout=subprocess.DEVNULL)
        game=stage/'unpacked/Main_Files'
        if not (game/'BattlefrontII.exe').is_file():raise SystemExit('Dedicated server executable missing after extraction.')
        prefix=stage/'swbf2-wine-prefix';prefix.mkdir()
        # Runtime DLL links are relative to the original default_pfx. Dereference once
        # before relocation; later instance copies must preserve dosdevices links.
        subprocess.run(['cp','-aL','--reflink=auto',str(runtime/'share/default_pfx')+'/.',str(prefix)],check=True)
        drives=prefix/'dosdevices';drives.mkdir(exist_ok=True)
        for name,target in (('c:','../drive_c'),('z:','/')):
            p=drives/name
            if p.is_symlink():p.unlink()
            p.symlink_to(target)
        (game/'.lisp-installed').write_text('Original Battlefront II v1.1 dedicated package; MD5 '+hashlib.md5(data).hexdigest()+'\n')
        for name,item in (('swbf2',game),('swbf2-wine-prefix',prefix)):
            target=templates/name
            if target.parent.resolve()!=templates.resolve():raise SystemExit('Invalid template path.')
            if target.exists():shutil.rmtree(target)
            shutil.move(str(item),str(target))
            subprocess.run(['chown','-R','lanserver:lanserver',str(target)],check=True)
    print('Battlefront II template installed. No firewall rules changed.')

if __name__=='__main__':main()
