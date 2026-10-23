#!/usr/bin/env python3
"""Generate original 9:16 motion-graphics Instagram Reels from editorial JSON.
Requires Pillow and ffmpeg. Produces silent videos with on-screen captions.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W,H = 720,1280
BG = (249,252,255)
CYAN = (0,143,164)
WHITE = (23,47,71)
MUTED = (82,112,136)
FPS=24
SECONDS=6

def font(n, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT,n)

def lines(draw, text, f, max_width):
    out, current=[], ""
    for word in str(text).split():
        test=(current+" "+word).strip()
        if draw.textbbox((0,0),test,font=f)[2] > max_width and current:
            out.append(current);current=word
        else: current=test
    if current:out.append(current)
    return out

def put(draw, text, x, y, f, color, width, max_lines=5, leading=1.27):
    all_lines=lines(draw,text,f,width)[:max_lines]
    for line in all_lines:
        draw.text((x,y),line,font=f,fill=color)
        y+=int(f.size*leading)
    return y

def scene(post, idx, total, date):
    image=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(image)
    for y in range(H):
        d.line((0,y,W,y),fill=(min(255,247+y//260),min(255,251+y//350),255))
    d.rounded_rectangle((34,40,686,1234),radius=30,outline=(197,224,234),width=3)
    d.rounded_rectangle((58,65,436,121),radius=16,fill=(221,248,250))
    d.text((77,80),"THE CYBER INTELLECT",font=font(22,True),fill=CYAN)
    d.text((59,156),post.get("category","CYBER INTELLIGENCE").upper()[:34],font=font(21,True),fill=CYAN)
    if idx==0:
        d.text((58,256),"THE BIG STORY",font=font(28,True),fill=MUTED)
        put(d,post["title"],58,335,font(56,True),WHITE,600,5,1.22)
        d.rounded_rectangle((58,905,661,1020),radius=22,fill=(226,245,252))
        put(d,"Here's what you need to know",83,934,font(26,True),WHITE,550,2)
    elif idx<=len(post.get("bullets",[])):
        bullet=post["bullets"][idx-1]
        d.text((58,250),f"EXPLAINED  {idx:02d}",font=font(30,True),fill=CYAN)
        d.ellipse((90,355,236,501),outline=CYAN,width=9)
        d.text((139,389),str(idx),font=font(59,True),fill=WHITE)
        d.line((164,505,164,622),fill=CYAN,width=7)
        d.rounded_rectangle((58,624,661,978),radius=24,fill=(237,247,251),outline=(191,223,233),width=2)
        put(d,bullet,82,688,font(38,True),WHITE,548,5,1.32)
    else:
        d.text((58,270),"WHAT TO DO NEXT",font=font(33,True),fill=CYAN)
        d.rounded_rectangle((58,410,661,760),radius=25,fill=(222,247,242))
        put(d,post.get("takeaway","Stay informed and verify sources."),82,482,font(41,True),WHITE,540,5,1.3)
        d.text((59,858),"FOLLOW FOR DAILY CYBER INTELLIGENCE",font=font(21,True),fill=CYAN)
    d.line((58,1122,661,1122),fill=(178,217,227),width=3)
    d.text((58,1150),"@thecyberintellect",font=font(24,True),fill=WHITE)
    d.text((58,1190),f"{date}   •   {idx+1}/{total}",font=font(19),fill=MUTED)
    return image

def run(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL)

def render_one(post, date, n, prefix=''):
    bullets=post.get("bullets",[])[:3]
    post={**post,"bullets":bullets}
    scenes=len(bullets)+2
    folder=ROOT/"media"/date
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/f"{prefix}{n:02d}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        temp=Path(tmp)
        clips=[]
        for idx in range(scenes):
            pic=temp/f"scene{idx}.png"
            scene(post,idx,scenes,date).save(pic)
            clip=temp/f"clip{idx}.mp4"
            run(["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1","-i",str(pic),
                "-vf",f"scale=800:1422,zoompan=z='min(zoom+0.00065,1.07)':d={FPS*SECONDS}:s=720x1280:fps={FPS},format=yuv420p",
                "-frames:v",str(FPS*SECONDS),"-c:v","libx264","-preset","veryfast",
                "-crf","28","-pix_fmt","yuv420p","-an",str(clip)])
            clips.append(clip)
        listing=temp/"clips.txt"
        listing.write_text("".join(f"file '{c}'\\n" for c in clips).replace("\\n","\n"))
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
             "-i",str(listing),"-c","copy","-movflags","+faststart",str(output)])
    print(f"REEL: {output} ({scenes*SECONDS}s)")

def main():
    for name in sys.argv[1:]:
        path=Path(name)
        content=json.loads(path.read_text(encoding="utf-8"))
        reels=content.get("reels",content.get("posts",[]))
        prefix="reel-" if "reels" in content else ""
        for i,post in enumerate(reels[:4],1):
            if not post.get("title") or not post.get("sources"):
                raise ValueError("Every Reel needs title and source URLs")
            render_one(post,path.stem,i,prefix)

if __name__=="__main__":
    main()
