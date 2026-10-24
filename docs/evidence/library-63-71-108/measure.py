import time,json
from pathlib import Path
from bible.library import catalogues
from bible.catalogue_cache import CatalogueCache
from bible.providers import PROVIDERS,EBIBLE
root=Path('/work/library-63-71-108');cache=CatalogueCache(root/'cache-after');runs=[]
for label,force,providers in [('cold-global',False,PROVIDERS),('warm-global',False,PROVIDERS),('explicit-ebible',True,(EBIBLE,))]:
 metrics={};first=[];start=time.monotonic()
 def ready(provider,items,error,timings):
  if items and not first:first.append(time.monotonic()-start)
  metrics[provider.id]={**timings,'resources':len(items),'error':str(error) if error else None}
 r=catalogues(providers,cache=cache,force=force,on_provider=ready)
 runs.append(dict(name=label,seconds=time.monotonic()-start,first_usable_provider_seconds=first[0] if first else None,resources=len(r.resources),errors=r.errors,providers=metrics))
 (root/'metadata-measurements.json').write_text(json.dumps(runs,indent=2)+'\n')
 print(label,len(r.resources),r.errors,flush=True)
