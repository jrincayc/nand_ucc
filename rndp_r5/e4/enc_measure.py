import math, collections, sys
import elay, eplace, eroute
def gam(n): n+=1; return 2*(n.bit_length())-1          # Elias gamma of n>=0 (as n+1)
def sg(d): return gam(abs(d))+ (1 if d else 0)         # sign + gamma(|d|)
nl=elay.read_nl('/tmp/eng.nl'); cmds,info=eroute.route(nl,eplace.order(nl,seed=1),R=14,Z=8)
nlate=info['nlate']; t=nlate[1]+nlate[2]
def norm(c):
    if c[0]=='track' and (c[3],c[2])>(c[5],c[4]): return ('track',c[1],c[4],c[5],c[2],c[3])
    return c
body=[norm(c) for c in cmds[:len(cmds)-t]]
def key(c):
    if c[0]=='place': return (0,c[1],c[3],c[2])
    if c[0]=='via': return (2,0,c[2],c[1])
    return (1,c[1],c[3],c[2])
# group by type, sorted by (y,x); delta coding of start point relative to previous of same group; track = orientation bit + length
tot=0; per=collections.Counter(); n=collections.Counter()
groups=collections.defaultdict(list)
for c in body: groups[key(c)[:2]].append(c)
for g,lst in groups.items():
    lst.sort(key=key); px=py=0
    for c in lst:
        if c[0]=='place': x,y=c[2],c[3]; extra=0
        elif c[0]=='via': x,y=c[1],c[2]; extra=0
        else:
            x,y=c[2],c[3]; L=abs(c[4]-c[2])+abs(c[5]-c[3]); extra=1+gam(L)      # orientation + length
        # sorted by y then x: dy>=0 ; if dy==0 dx>0 ; else x absolute-ish delta
        dy=y-py
        b=gam(dy)+ (gam(x-px-1) if dy==0 else sg(x-px))
        b+=extra
        per[g[0] if g[0]!='' else 'x']+=b; n[c[0]]+=1; tot+=b; px,py=x,y
print('commands',len(body),'bits',tot,'bits/cmd',tot/len(body),'bits/gate',tot/696,'bytes',tot/8)
print({k:(n[k],) for k in n}); print(dict(per))

# ---- word-format study: one 24-bit word per command, class sections, deltas from previous command of the section
print('--- word format study')
tot_words=0; esc=0; hdr=0
for g,lst in sorted(groups.items()):
    lst.sort(key=key); px=py=0; hdr+=1
    for c in lst:
        if c[0]=='place': x,y=c[2],c[3]; ln=0
        elif c[0]=='via': x,y=c[1],c[2]; ln=0
        else: x,y=c[2],c[3]; ln=abs(c[4]-c[2])+abs(c[5]-c[3])
        dy=y-py; dx=x-px
        ok = 0<=dy<=30 and -256<=dx<=255 and ln<=255        # dy 5b, dx 9b signed, len 8b
        if c[0]=='track': ok = ok and True
        tot_words+=1 if ok else 3          # escape = header word + 2 absolute words (pessimistic)
        esc+= 0 if ok else 1
        px,py=x,y
print('groups',len(groups),'words',tot_words,'escapes',esc,'cmds',len(body))

print('--- distributions')
for g,lst in sorted(groups.items()):
    px=py=0; dys=collections.Counter(); dxs=collections.Counter(); lens=collections.Counter()
    for c in lst:
        if c[0]=='place': x,y=c[2],c[3]; ln=0
        elif c[0]=='via': x,y=c[1],c[2]; ln=0
        else: x,y=c[2],c[3]; ln=abs(c[4]-c[2])+abs(c[5]-c[3])
        dys[min(y-py,40)]+=1; dxs[max(-40,min(x-px,40))//8*8]+=1; lens[min(ln,200)//16*16]+=1; px,py=x,y
    print(g,len(lst),'dy',sorted(dys.items())[:12],'dx',sorted(dxs.items()),'len',sorted(lens.items()))
