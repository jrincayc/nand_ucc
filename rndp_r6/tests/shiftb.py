import sys
dx,dy=int(sys.argv[3]),int(sys.argv[4])
o=open(sys.argv[2],'w')
for l in open(sys.argv[1]):
    t=l.split()
    if not t: continue
    if t[0]=='place': t[2]=str(int(t[2])+dx); t[3]=str(int(t[3])+dy)
    elif t[0]=='via': t[1]=str(int(t[1])+dx); t[2]=str(int(t[2])+dy)
    else: t[2]=str(int(t[2])+dx);t[3]=str(int(t[3])+dy);t[4]=str(int(t[4])+dx);t[5]=str(int(t[5])+dy)
    o.write(' '.join(t)+'\n')
