import sys; sys.path.insert(0,'.')
import engine
def sizes(a):
    pc=0; marks=[]
    for it in a.items:
        if it[0]=='L': marks.append((pc,it[1]))
        elif it[0]=='B': pc+=len(it[1])
        else: pc+=2
    return marks,pc
if __name__=='__main__':
    a,plan,V,sl=engine.make_program(int(sys.argv[1]) if len(sys.argv)>1 else 6)
    marks,total=sizes(a)
    named=[m for m in marks if m[1] in ('traverse','place1','ref','wnodes','add16','sub16','shl1','getbit','getbits','readEG','halt','seg_a','end')]
    for (p,n),(q,_) in zip(named,named[1:]+[(total,'')]): print(f'{n:8s} {q-p:5d}')
    print('main code (before halt):', [p for p,n in marks if n=='halt'][0])
