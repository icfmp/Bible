"""Measure real per-provider cold/warm catalogue startup without timing fixtures."""
import argparse
import json
from pathlib import Path
import time
from bible.catalogue_cache import CatalogueCache
from bible.library import catalogues


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');args=parser.parse_args()
    cache=CatalogueCache(Path(args.profile)/'catalogue-cache')
    for name,force in [('cold',True),('warm',False)]:
        start=time.monotonic();events=[]
        def delivered(provider,items,error,timings):
            events.append(dict(provider=provider.id,at_seconds=time.monotonic()-start,
                               resources=len(items),error=error,**timings))
        result=catalogues(cache=cache,on_provider=delivered,force=force)
        print(json.dumps(dict(mode=name,first_seconds=events[0]['at_seconds'],
                              total_seconds=time.monotonic()-start,resources=len(result.resources),
                              providers=events)),flush=True)


if __name__=='__main__':main()
