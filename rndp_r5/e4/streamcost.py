import sys, collections
import elay, eplace, eroute
def regs_of(c):
    if c[0]=='place': _,k,x,y,rot,val=c; return {0:x&255,1:(x>>8)&255,2:y&255,3:(y>>8)&255,8:k,9:rot,10:val},1
    if c[0]=='track': _,l,x0,y0,x1,y1=c; return {0:x0&255,1:(x0>>8)&255,2:y0&255,3:(y0>>8)&255,4:x1&255,5:(x1>>8)&255,6:y1&255,7:(y1>>8)&255,10:l},4
    _,x,y=c; return {0:x&255,1:(x>>8)&255,2:y&255,3:(y>>8)&255},5
def cost(cmds):
    cur={}; n=0
    for c in cmds:
        r,code=regs_of(c)
        for k,v in r.items():
            if cur.get(k)!=v: n+=1; cur[k]=v
        n+=1
    return n
def key(c):
    if c[0]=='place': return (0,c[1],c[3],c[2])
    if c[0]=='via': return (2,0,c[2],c[1])
    return (1,c[1],c[3],c[2])
if __name__=='__main__':
    nl=elay.read_nl('/tmp/eng.nl'); R=int(sys.argv[1]) if len(sys.argv)>1 else 22
    cmds,info=eroute.route(nl,eplace.order(nl,seed=1),R=R)
    nl_=info['nlate']; body=cmds[:len(cmds)-nl_[1]-nl_[2]]; tail=cmds[len(cmds)-nl_[1]-nl_[2]:]
    print('cmds',len(cmds),'raw order words',cost(cmds))
    sb=sorted(body,key=key); print('sorted words',cost(sb+tail))
    # normalise tracks so that (x0,y0)<=(x1,y1) in sort order
    def norm(c):
        if c[0]=='track' and (c[3],c[2])>(c[5],c[4]): return ('track',c[1],c[4],c[5],c[2],c[3])
        return c
    sb=sorted([norm(c) for c in body],key=key); print('sorted+norm words',cost(sb+tail))
