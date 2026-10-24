import elay, eplace, maze
nl=elay.read_nl('/tmp/eng.nl'); order=eplace.order(nl,seed=1)
orig=maze.search
def s2(G,net,tree,goals,goal_l0):
    p=orig(G,net,tree,goals,goal_l0)
    if p is None and not getattr(s2,'done',0):
        s2.done=1
        (gx,gy),=goals
        print('net',net,'goal',goals,'tree',sorted(tree)[:4])
        for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1)):
            x,y=gx+dx,gy+dy; ix,iy=x-G.x0,y-G.y0
            print((dx,dy),'pad',G.pad[iy][ix],'occ',G.occ[0][iy][ix],G.occ[1][iy][ix],'ok0',G.ok(x,y,0,net),'ok1',G.ok(x,y,1,net))
    return p
maze.search=s2
cmds,info=maze.route_engine(nl,order,932,100,pitch=(6,6),R=24)
