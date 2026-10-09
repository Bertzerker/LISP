"""Owned persistent world settings, build compatibility and port isolation."""
import json,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from zomboid_adapter import ZomboidAdapter
from sevendays_adapter import SevenDaysAdapter

class SurvivalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for game in ['zomboid','sevendays']:
   p=self.root/'templates'/game;p.mkdir(parents=True);(p/'.lisp-source.json').write_text(json.dumps({'buildid':'new-build'}))
  p=self.root/'templates/sevendays';(p/'serverconfig.xml').write_text('<ServerSettings><property name="ServerPassword" value="old-password"/><property name="TelnetPassword" value="old-admin"/></ServerSettings>')
  for name in ['Navezgane','Pregen06k01','Empty']:
   d=p/'Data/Worlds'/name;d.mkdir(parents=True)
   for f in ['main.ttw']+([] if name=='Empty' else ['map_info.xml','spawnpoints.xml']):(d/f).touch()
  p=self.root/'templates/zomboid';(p/'media/lua/shared/Sandbox').mkdir(parents=True);(p/'media/lua/shared/Sandbox/Apocalypse.lua').write_text('return { Zombies = 4 }')
  d=p/'media/maps/Rosewood, KY';d.mkdir(parents=True);(d/'map.info').touch();(d/'spawnpoints.lua').touch()
 def tearDown(self):self.tmp.cleanup()
 def prepare(self,cls,ident='123456abcdef',world='new',owner=2,role='player'):
  a=cls(self.root);home=self.root/'instances'/ident;home.mkdir(parents=True);level='Rosewood, KY' if cls is ZomboidAdapter else 'Navezgane'
  def copy(args,**kw):
   # Only source files required by preparation, with no real game processes.
   if cls is SevenDaysAdapter:(home/'game/serverconfig.xml').write_text((a.path/'serverconfig.xml').read_text())
   else:
    p=home/'game/media/lua/shared/Sandbox';p.mkdir(parents=True);(p/'Apocalypse.lua').write_text('return { Zombies = 4 }')
  with patch('subprocess.run',side_effect=copy):args,cwd=a.prepare_request(home,27015,'coop',level,4,'JoinTest123','AdminTest123',[],[],{'world':world,'worldName':'Test World','_actor':{'id':owner,'role':role}})
  return a,home,args
 def test_sevendays_settings_do_not_inherit_passwords_and_supported_ports(self):
  a,home,args=self.prepare(SevenDaysAdapter);props={p.get('name'):p.get('value') for p in ET.parse(home/'serverconfig.xml').getroot()}
  self.assertEqual(props['ServerPassword'],'JoinTest123');self.assertEqual(props['TelnetPassword'],'AdminTest123');self.assertEqual(props['UserDataFolder'],str(a._world));self.assertNotIn('SaveGameFolder',props)
  self.assertEqual(props['PlayerKillingMode'],'0');self.assertEqual(props['ServerVisibility'],'0');self.assertEqual(props['WebDashboardEnabled'],'false');self.assertEqual(props['TelnetPort'],'28015')
  self.assertEqual(a.maps(),['Navezgane','Pregen06k01']);self.assertEqual(a.reserved_ports(27015)[1][0],27017)
  self.assertTrue(set(p for p,t in a.reserved_ports(27015)).isdisjoint(p for p,t in a.reserved_ports(27016)))
 def test_world_owner_and_build_guards_for_both_games(self):
  for cls in [SevenDaysAdapter,ZomboidAdapter]:
   with self.subTest(game=cls.id):
    ident=('abcd1234' if cls is SevenDaysAdapter else 'dcba1234')+'0001';a,home,args=self.prepare(cls,ident)
    self.assertEqual(a.worlds()[0]['ownerId'],2)
    with self.assertRaises(PermissionError):self.prepare(cls,ident[:-1]+'3',world=ident,owner=3)
    a2,home2,args=self.prepare(cls,ident[:-1]+'4',world=ident,owner=2);self.assertEqual(a2._world,a._world)
    p=a.path/'.lisp-source.json';p.write_text(json.dumps({'buildid':'future-build'}));self.assertEqual(a.worlds(),[])
    with self.assertRaises(ValueError):self.prepare(cls,ident[:-1]+'5',world=ident,owner=2)
 def test_world_path_injection_rejected(self):
  for cls in [SevenDaysAdapter,ZomboidAdapter]:
   a=cls(self.root)
   with self.assertRaises(ValueError):a.prepare_request(self.root/'home',27015,'coop','Navezgane',2,'','',[],[],{'world':'../other','_actor':{'id':2,'role':'player'}})
if __name__=='__main__':unittest.main()
