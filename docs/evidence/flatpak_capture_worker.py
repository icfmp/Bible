"""Delegate screenshots to the Xvfb parent; the Flatpak runtime has no Pillow."""
import json,socket,sys,types,runpy
connection=socket.socket(socket.AF_UNIX);connection.connect(sys.argv[1]);stream=connection.makefile('rwb')
def rpc(method,*args):
 stream.write((json.dumps([method,*args])+'\n').encode());stream.flush()
 result=json.loads(stream.readline());assert 'error' not in result,result
 return result.get('value')
class Capture:
 def save(self,path):rpc('save',path)
 def getpixel(self,point):return rpc('pixel',point)
def grab():rpc('grab');return Capture()
sys.modules['PIL']=types.SimpleNamespace(ImageGrab=types.SimpleNamespace(grab=grab))
import bible
assert bible.__file__.startswith('/app/'),bible.__file__
print('PACKAGED IMPORT:',bible.__file__,'actual Xvfb screenshots delegated to parent Pillow',flush=True)
script=sys.argv[2];sys.argv=sys.argv[2:];runpy.run_path(script,run_name='__main__')
