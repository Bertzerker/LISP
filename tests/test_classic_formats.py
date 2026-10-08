"""Malformed LAN responses and REZ directories must fail closed."""
import struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from classic_windows_adapter import wolf_info
from rez_index import entries

class Formats(unittest.TestCase):
 def test_unrelated_and_truncated_query_rejected(self):
  for packet in (b'\\hostname\\othergame',b'\xff\xffinfoResponse\0',b'\xff\xffinfoResponse\0'+b'\0'*16+b'si_map\0unterminated'):
   with self.assertRaises((ValueError,IndexError)):wolf_info(packet)
 def test_invalid_rez_header_and_directory_bounds(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'archive.rez';path.write_bytes(b'not a resource archive')
   with self.assertRaises(ValueError):list(entries(path))
   header=bytearray(143);header[:2]=b'\r\n';header[126]=26;struct.pack_into('<III',header,127,1,1024,100);path.write_bytes(header)
   with self.assertRaises(ValueError):list(entries(path))
 def test_rez_path_traversal_rejected(self):
  directory=struct.pack('<IIII',1,143,1,0)+b'..\0';header=bytearray(143);header[:2]=b'\r\n';header[126]=26;struct.pack_into('<III',header,127,1,143,len(directory))
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'archive.rez';path.write_bytes(header+directory)
   with self.assertRaises(ValueError):list(entries(path))
 def test_rez_cycle_rejected(self):
  directory=struct.pack('<IIII',1,143,18,0)+b'a\0';header=bytearray(143);header[:2]=b'\r\n';header[126]=26;struct.pack_into('<III',header,127,1,143,len(directory))
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'archive.rez';path.write_bytes(header+directory)
   with self.assertRaises(ValueError):list(entries(path))

if __name__=='__main__':unittest.main()
