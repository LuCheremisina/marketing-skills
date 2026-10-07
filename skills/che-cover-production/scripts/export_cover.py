#!/usr/bin/env python3
"""Export an existing image as bounded WebP; retain the original."""
import argparse, sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path);parser.add_argument("output",type=Path)
    parser.add_argument("--width",type=int,default=1200);parser.add_argument("--height",type=int,default=675)
    parser.add_argument("--max-kb",type=int,default=200)
    args=parser.parse_args()
    if min(args.width,args.height,args.max_kb)<=0:parser.error("dimensions and max-kb must be positive")
    if args.source.resolve()==args.output.resolve():parser.error("output must differ from source")
    if args.output.exists():parser.error("output already exists; choose a new reviewed destination")
    try:from PIL import Image,ImageOps
    except ImportError:print("Pillow is required for export",file=sys.stderr);return 2
    import io
    try:
        with Image.open(args.source) as original:
            image=ImageOps.fit(ImageOps.exif_transpose(original).convert("RGB"),(args.width,args.height))
            for quality in range(95,9,-5):
                buffer=io.BytesIO();image.save(buffer,"WEBP",quality=quality,method=6)
                data=buffer.getvalue()
                if len(data)<=args.max_kb*1024:
                    args.output.parent.mkdir(parents=True,exist_ok=True)
                    with args.output.open("xb") as f:f.write(data)
                    print(f"PASS: {args.width}x{args.height}, {len(data)} bytes, quality {quality}");return 0
        print("Cannot satisfy size limit without changing dimensions",file=sys.stderr);return 1
    except (OSError,ValueError) as exc:print(f"Export failed: {exc}",file=sys.stderr);return 1
if __name__=="__main__":sys.exit(main())
