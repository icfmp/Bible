"""Real X11 capture bridge; never synthesize or transform screenshot pixels."""
import json,socket,subprocess,sys,threading
from pathlib import Path
from PIL import ImageGrab
path='/evidence/bible-public-capture.sock';Path(path).unlink(missing_ok=True)
server=socket.socket(socket.AF_UNIX);server.bind(path);server.listen(1)
def capture():
 conn,_=server.accept();stream=conn.makefile('rwb');image=None
 for line in stream:
  try:
   method,*args=json.loads(line)
   if method=='grab':image=ImageGrab.grab();value=None
   elif method=='save':image.save(args[0]);value=None
   elif method=='pixel':value=image.getpixel(tuple(args[0]))
   else:raise ValueError(method)
   answer={'value':value}
  except Exception as error:answer={'error':str(error)}
  stream.write((json.dumps(answer)+'\n').encode());stream.flush()
 conn.close()
thread=threading.Thread(target=capture,daemon=True);thread.start()
command=['flatpak','run','--system','--filesystem=/src:ro','--filesystem=/evidence',
 '--env=PYTHONPATH=/app/lib/bible-python:/src','--command=python3','io.github.icfmp.Bible//alpha',
 '/src/docs/evidence/flatpak_capture_worker.py',path,*sys.argv[1:]]
try:result=subprocess.run(command);sys.exit(result.returncode)
finally:server.close();Path(path).unlink(missing_ok=True)
