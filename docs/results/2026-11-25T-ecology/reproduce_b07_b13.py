import json, sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
from brainos import Runtime, Refused
from brainos.__main__ import install
from brainos.development import CapabilityDemand, CompositionSearch
from brainos import providers, graphs
P={"parse":"parse_csv","total":"sum","total_loop":"sum_loop","count":"count","length":"text_length","negate":"negate"}
C={"parse":[("1,2",[1,2])],"total":[([1,2],3)],"total_loop":[([1,2],3)],"count":[([1,2],2)],"length":[("ab",2)],"negate":[(3,-3)]}
F={}
with tempfile.TemporaryDirectory() as d:
    r=Runtime(Path(d)/"c.db"); install(r,P,C)
    dev=r.resources.create_budget("dev",{"attempts":500}); val=r.resources.create_budget("dev",{"attempts":100})
    s=CompositionSearch(r)
    g1=s.acquire(CapabilityDemand("csv-sum","text","integer",(("1,2,3",6),)),"dev",dev,[("4,5",9)],validation_budget=val)
    # B07: gen-2 demand needs csv-sum -> negate (depth 2 with composite); primitive-only at depth 2 cannot reach
    g2=s.acquire(CapabilityDemand("csv-neg-sum","text","integer",(("1,2,3",-6),),max_depth=2),"dev",dev,[("4,5",-9)],validation_budget=val)
    nested=dict(input="text",output="integer",output_node="n1",nodes=[dict(id="n0",provider=g1["provider"],input="$input"),dict(id="n1",provider=r.manifest()["bindings"]["negate"],input="n0")])
    try: r.registry.register_graph(nested,"x"); nested_ok=True; err=""
    except Refused as e: nested_ok=False; err=str(e)
    F["B07"]=dict(reproduced=g2["status"]=="NON_ATTAINMENT" and not nested_ok, gen1=g1["status"], gen2_depth2=g2["status"], nested_graph_error=err)
    # B08: capability field equals role/demand name; alternative must be a different role
    spec=r.registry.resolve(g1["provider"])
    alt=s.acquire(CapabilityDemand("csv-sum","text","integer",(("1,2,3",6),)),"dev",dev,[("4,5",9)],validation_budget=val,exclude_paths=(tuple(g1["path"]),))
    b=r.manifest()["bindings"]
    F["B08"]=dict(reproduced=spec["capability"]=="csv-sum" and alt["status"]=="ACQUIRED" and b["csv-sum"]==alt["provider"],
        capability_field=spec["capability"], note="second provider of the same capability replaced the first binding; no population holds both",
        first_still_bound=b["csv-sum"]==g1["provider"])
    # B10: kernel validation budget fixed
    key=r.store.get("system","validation-budget")["id"]; kb=r.resources.budget(key,"_kernel_validation")
    n=0
    try:
        while n<200:
            c=r.transactor.stage({"total":r.registry.register("sum_loop")}); r.transactor.validate(c,{"total":[([1],1)]}); n+=1
    except Refused as e: err=str(e)
    F["B10"]=dict(reproduced=n<200, validations_before_exhaustion=n, error=err, capacity=kb["capacity"])
    # B11: no overall deadline; a slow runner stalls search beyond any bound
    slow=r.runner.compute
    def lag(*a,**k): time.sleep(0.3); return slow(*a,**k)
    t=time.monotonic()
    with patch.object(r.runner,"compute",side_effect=lag):
        list(s.discover(CapabilityDemand("x","text","integer",(("1",1),("2",2),("3",3)),max_candidates=8),"dev",dev))
    F["B11"]=dict(reproduced="deadline" not in CapabilityDemand.__dataclass_fields__, elapsed_seconds=round(time.monotonic()-t,2),
                  fields=list(CapabilityDemand.__dataclass_fields__))
    # B12: disconnected node accepted and executed
    pr,tot,cnt=b["parse"],b["total"],b["count"]
    dead=dict(input="text",output="integer",output_node="n1",nodes=[dict(id="n0",provider=pr,input="$input"),dict(id="n1",provider=tot,input="n0"),dict(id="n2",provider=cnt,input="n0")])
    try:
        gid=r.registry.register_graph(dead,"dead"); spec=r.registry.resolve(gid); ok=True
    except Refused: ok=False
    F["B12"]=dict(reproduced=ok, node_count=len(spec["nodes"]) if ok else None, cost=spec["cost"] if ok else None, note="n2 does not reach output_node n1 but is admitted and charged")
    # B13: construction record fields
    rec=r.store.find("construction")[0]
    F["B13"]=dict(reproduced=not any(k in rec for k in ("manifest_revision","demand_definition","evaluation","costs")), fields=sorted(rec))
    r.close()
# B09: indirect shared-resource interference (needs differing footprints)
sys.path.insert(0,"tools"); from dep_closure import compute_closure
from brainos.fabric import ComputationalFabric
class S: 
    def __init__(s,rows): s.rows=rows
    def find(s,k): return s.rows
rows=[dict(id="A",kind="primitive",footprint={"resources":["r1"],"failure_domains":[]},dependencies=[]),
      dict(id="B",kind="primitive",footprint={"resources":["r1","r2"],"failure_domains":[]},dependencies=[]),
      dict(id="C",kind="primitive",footprint={"resources":["r2"],"failure_domains":[]},dependencies=[])]
fab=ComputationalFabric(S(rows),None,None,None,None)
got=set(fab.impact("A","resources")["affected"]); ref,_=compute_closure({"A"},[],{x["id"]:set(x["footprint"]["resources"]) for x in rows})
F["B09"]=dict(reproduced=got!=set(ref), runtime=sorted(got), reference=sorted(ref), enforcement="impact() returns an advisory action; only registry.exclude blocks use")
print(json.dumps(F,indent=1))
