#!/usr/bin/env python3
"""Animated 30s narrated Reels: dynamic text/diagrams, original motion graphics, natural TTS."""
import json, math, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
W,H,FPS,SCENE_SEC=540,960,15,6
DARK=(23,49,72); BLUE=(0,138,168); LIGHT=(249,252,255); GREY=(92,116,135)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(s,b=False): return ImageFont.truetype(BOLD if b else FONT,s)
def call(cmd, **kwargs): return subprocess.run(cmd,check=True,**kwargs)
def wrap(d,txt,f,width):
    rows=[];cur=""
    for word in str(txt).split():
        candidate=(cur+" "+word).strip()
        if d.textbbox((0,0),candidate,font=f)[2]>width and cur:
            rows.append(cur);cur=word
        else:cur=candidate
    if cur:rows.append(cur)
    return rows
def textblock(d,txt,x,y,f,color,width,maxlines=6,space=1.3):
    for line in wrap(d,txt,f,width)[:maxlines]:
        d.text((x,y),line,font=f,fill=color);y+=int(f.size*space)
    return y
def smooth(t): return max(0,min(1,t))**2*(3-2*max(0,min(1,t)))
def frame(post,idx,progress,count):
    im=Image.new("RGB",(W,H),LIGHT);d=ImageDraw.Draw(im)
    for y in range(H):d.line((0,y,W,y),fill=(246,251,255-int(y/H*4)))
    d.rounded_rectangle((20,18,W-20,H-18),radius=22,outline=(187,222,232),width=2)
    d.rounded_rectangle((38,36,345,78),radius=12,fill=(217,245,250))
    d.text((52,47),"THE CYBER INTELLECT",font=font(18,True),fill=BLUE)
    d.text((38,110),post.get("category","CYBER INTELLIGENCE").upper()[:34],font=font(16,True),fill=BLUE)
    d.text((38,146),f"{idx+1:02d} / {count:02d}",font=font(17),fill=GREY)
    d.rounded_rectangle((38,188,W-38,194),radius=3,fill=(220,235,242))
    d.rounded_rectangle((38,188,38+int((W-76)*(idx+progress)/count),194),radius=3,fill=BLUE)
    bullets=post.get("bullets",[])[:3]
    if idx==0:
        d.text((38,244),"IN 30 SECONDS",font=font(23,True),fill=BLUE)
        end=int(220*smooth(progress*1.5))
        d.rounded_rectangle((38,302,38+end,309),radius=3,fill=(255,171,75))
        lines=wrap(d,post["title"],font(42,True),465)
        visible=max(1,int(sum(map(len,lines))*smooth(progress*1.8)))
        textblock(d," ".join(lines)[:visible],38,360,font(42,True),DARK,465,6,1.23)
    elif idx<=len(bullets):
        label=["WHAT HAPPENED","WHY IT MATTERS","WHAT TO DO"][min(idx-1,2)]
        d.text((38,238),label,font=font(25,True),fill=BLUE)
        cx=118+int(12*math.sin(progress*math.pi*2));cy=360
        d.ellipse((cx-55,cy-55,cx+55,cy+55),outline=BLUE,width=7)
        d.text((cx-14,cy-29),str(idx),font=font(48,True),fill=DARK)
        for n in range(3):
            x=225+n*72;yy=352+int(15*math.sin(progress*math.pi*2+n))
            d.rounded_rectangle((x,yy,x+46,yy+46),radius=8,fill=[(213,242,250),(227,245,235),(255,240,215)][n])
            if n>0:d.line((x-25,yy+23,x-3,yy+23),fill=BLUE,width=4)
        d.rounded_rectangle((38,458,W-38,750),radius=22,fill=(229,245,252),outline=(190,222,234),width=2)
        words=bullets[idx-1].split()
        shown=max(1,int(len(words)*smooth(progress*1.55)))
        textblock(d," ".join(words[:shown]),58,495,font(29,True),DARK,420,7,1.34)
    else:
        d.text((38,255),"YOUR NEXT MOVE",font=font(26,True),fill=BLUE)
        height=int(250*smooth(progress*1.4))
        d.rounded_rectangle((38,342,W-38,342+max(1,height)),radius=22,fill=(222,247,238))
        words=post.get("takeaway","Stay informed and verify sources.").split()
        shown=max(1,int(len(words)*smooth(progress*1.45)))
        textblock(d," ".join(words[:shown]),58,378,font(30,True),DARK,416,5,1.35)
        d.text((38,745),"FOLLOW FOR DAILY AI + CYBER NEWS",font=font(18,True),fill=BLUE)
    # Animated lower-third ticker and caption
    d.line((38,823,W-38,823),fill=(188,224,233),width=2)
    d.text((38,843),"@thecyberintellect",font=font(21,True),fill=DARK)
    dot_x=38+int(445*progress)
    d.ellipse((dot_x,895,dot_x+12,907),fill=(255,159,74))
    return im
def speak(text,dest):
    # Cloud neural voice when available, deterministic offline fallback.
    try:
        call(["edge-tts","--voice","en-US-AriaNeural","--rate","+5%","--text",text,"--write-media",str(dest)],
             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=35)
        if dest.exists() and dest.stat().st_size>2000:return dest
    except Exception as e:print("Neural voice unavailable, using offline fallback:",e,flush=True)
    wav=dest.with_suffix(".wav")
    call(["espeak-ng","-v","en-us","-s","155","-w",str(wav),text],stdout=subprocess.DEVNULL)
    return wav
def audio_length(p):
    result=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)])
    return float(result)
def narration(post):
    if post.get("voiceover"):
        return post["voiceover"]
    b=post.get("bullets",[])[:3]
    pieces=[post["title"]+"."]+[x[:120].rsplit(" ",1)[0]+"." if len(x)>120 else x for x in b]
    pieces.append(post.get("takeaway","Follow The Cyber Intellect."))
    return " ".join(pieces)
def render(post,day,n,prefix):
    post={**post,"bullets":post.get("bullets",[])[:3]}
    count=len(post["bullets"])+2
    duration=count*SCENE_SEC
    folder=ROOT/"media"/day;folder.mkdir(parents=True,exist_ok=True)
    output=folder/f"voice-{prefix}{n:02d}.mp4"
    with tempfile.TemporaryDirectory() as tempdir:
        td=Path(tempdir);silent=td/"silent.mp4";speech=td/"speech.mp3";voice=speak(narration(post),speech)
        cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-vcodec","rawvideo","-s",f"{W}x{H}","-pix_fmt","rgb24","-r",str(FPS),"-i","-","-c:v","libx264","-preset","ultrafast","-crf","27","-pix_fmt","yuv420p","-movflags","+faststart",str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for idx in range(count):
                for tick in range(SCENE_SEC*FPS):
                    im=frame(post,idx,tick/(SCENE_SEC*FPS-1),count)
                    proc.stdin.write(im.tobytes())
            proc.stdin.close()
            if proc.wait()!=0:raise RuntimeError("FFmpeg video encoding failed")
        finally:
            if proc.poll() is None:proc.kill()
        length=audio_length(voice)
        tempo=length/max(1,duration-1)
        # Tempo >1 speeds up long narration; tempo <1 slows short narration.
        tempo=max(.5,min(2.0,tempo))
        call(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(silent),"-i",str(voice),
              "-filter_complex",f"[1:a]atempo={tempo:.4f},apad=pad_dur=2[a]",
              "-map","0:v","-map","[a]","-t",str(duration),"-c:v","copy","-c:a","aac","-b:a","128k",
              "-movflags","+faststart",str(output)],stdout=subprocess.DEVNULL)
    print(f"READY {output} ({duration}s) with narration",flush=True)
def main():
    for filename in sys.argv[1:]:
        path=Path(filename);data=json.loads(path.read_text())
        posts=data.get("reels",data.get("posts",[]))
        prefix="reel-" if "reels" in data else ""
        for i,post in enumerate(posts[:4],1):
            if not post.get("sources"):raise ValueError("Source URL required")
            render(post,path.stem,i,prefix)
if __name__=="__main__":main()
