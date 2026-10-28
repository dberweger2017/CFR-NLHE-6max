import copy
import math
import json
from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from scripts import nplayer_passive_learning_qualification as q


def owner():
    return dict(study="PR457", status="owner-approved", seed=q.SEED, targets=[128,512],
                cap=2_000_000, threads=2, epsilon=.02, watch_hands=512, allocation_seconds=1200)


def native(mode="initial"):
    arms=[]
    for name in ["control","exploration"]:
        endpoints=[]
        for n in [128,512]:
            learning=dict(watch=[watch("0011",n*24)],watch_keys=1,
                 cells=[dict(street=s,family=f)for s in range(4)for f in ["P0","P1","P2","other","merged-families"]],
                 qualified_retained_watch_keys=0,fully_zero_final_rows=1,admitted_rows=10,all_root_contexts=n*24)
            endpoints.append(dict(iteration=n,entries=10,learning=learning,row_audit=dict(by_street=[[10,0,0,1,0],[0]*5,[0]*5,[0]*5]),
                         row_proof=dict(logical_rows_sha256="pinned",row_copy_retained=mode=="initial",write_or_hash_seconds=1),
                         added_training_seconds=1,readout_seconds=2))
        arms.append(dict(name=name,endpoints=endpoints))
    return dict(status="native-complete-proof-pending",mode=mode,arms=arms,wall_seconds=7,startup_and_watch_seconds=1)


def watch(key,roots,qualifies=False):
    def evidence(ok):
        n=4 if ok else 0
        x=dict(all_root_contexts=roots,replicated_learning_proxy=ok,encountered_root_groups=n,
               retained_root_groups=n,declined_root_groups=0,retained_nonzero_regret_roots=n,retained_positive_average_roots=n)
        for k in ["regret_raw","regret_linear","average_raw","average_linear"]:
            x[k+"_coefficients"]=dict(events=n,sum=n,sum_squares=n,ess=n)
        return x
    x=evidence(qualifies)
    x.update(key=key,all_history_key_proxy=qualifies,public_watch_metadata=dict(families=[0]),
             qualifying_target_families=["P0"]if qualifies else [],
             by_actual_training_family={f:evidence(qualifies and f=="P0")for f in ["P0","P1","P2","other","merged-families"]})
    return x


class QualificationTests(unittest.TestCase):
    def test_main_requires_exact_scope_and_finite_accepted_quote(self):
        good=owner();q.acceptance(good,dict(reserved_seconds=1199))
        for key,bad in [("study","other"),("seed",1),("targets",[128,1024]),("cap",4_000_000),
                        ("threads",4),("epsilon",.1),("watch_hands",1),("status","pending"),
                        ("allocation_seconds",1198),("allocation_seconds",math.inf),("allocation_seconds",math.nan)]:
            x=dict(good);x[key]=bad
            with self.assertRaises(ValueError):q.acceptance(x,dict(reserved_seconds=1199))

    def test_reproduction_compares_values_not_timing_or_retained_copy(self):
        a,b=native(),native("repeat");b["wall_seconds"]=99;b["arms"][0]["endpoints"][0]["readout_seconds"]=99
        result=q.verify(a,b);self.assertEqual(result["status"],"settled");self.assertFalse(result["small_qualification_signal"])
        for change in ["rows","watch","cell"]:
            b=native("repeat");e=b["arms"][0]["endpoints"][0]
            if change=="rows":e["row_proof"]["logical_rows_sha256"]="corrupt"
            elif change=="watch":e["learning"]["watch"][0]["replicated_learning_proxy"]=True
            else:e["learning"]["cells"][0]={"altered":1}
            with self.assertRaises(ValueError):q.verify(a,b)

    def test_never_hit_and_sparse_inventory_cannot_be_dropped(self):
        for kind in ["watch","cells","endpoint","arm"]:
            a=native()
            if kind=="watch":a["arms"][0]["endpoints"][0]["learning"]["watch"]=[]
            elif kind=="cells":a["arms"][0]["endpoints"][0]["learning"]["cells"]=[]
            elif kind=="endpoint":a["arms"][0]["endpoints"].pop()
            else:a["arms"].pop()
            with self.assertRaises(ValueError):q.verify(a,copy.deepcopy(a))

    def test_proxy_breadth_and_zero_capacity_guard_are_both_required(self):
        a=native();e=a["arms"][1]["endpoints"][-1]["learning"]
        e["qualified_retained_watch_keys"]=5
        for arm in a["arms"]:
            for endpoint in arm["endpoints"]:
                l=endpoint["learning"];l["watch"]=[watch(str(i),endpoint["iteration"]*24,arm["name"]=="exploration"and endpoint["iteration"]==512 and i<5)for i in range(10)];l["watch_keys"]=10
        self.assertTrue(q.verify(a,copy.deepcopy(a))["small_qualification_signal"])
        e["fully_zero_final_rows"]=2
        a["arms"][1]["endpoints"][-1]["row_audit"]["by_street"][0][3]=2
        self.assertFalse(q.verify(a,copy.deepcopy(a))["small_qualification_signal"])

    def test_reproducing_the_same_wrong_proxy_does_not_pass(self):
        a=native();e=a["arms"][1]["endpoints"][-1]["learning"];e["qualified_retained_watch_keys"]=1
        with self.assertRaises(ValueError):q.verify(a,copy.deepcopy(a))
        a=native();w=a["arms"][0]["endpoints"][0]["learning"]["watch"][0];w["regret_raw_coefficients"]["ess"]=5
        with self.assertRaises(ValueError):q.verify(a,copy.deepcopy(a))

    def test_learning_on_an_aliased_other_history_does_not_qualify_passive(self):
        w=watch("x",100,True)
        w["by_actual_training_family"]["P0"],w["by_actual_training_family"]["other"]=w["by_actual_training_family"]["other"],w["by_actual_training_family"]["P0"]
        w["replicated_learning_proxy"]=False;w["qualifying_target_families"]=[]
        self.assertFalse(q.proxy(w))

    def test_main_requires_named_review_and_settled_calibration(self):
        with TemporaryDirectory()as d:
            root=Path(d);source={"example":"source-pin"}
            for name in ["binary","thermal","table"]:(root/name).write_text(name)
            review=dict(status="approved",study="PR457",reviewer="independent",unresolved=[],
                        scope="perturbed-policy-math-information-qualification-v1",source_sha256=q.digest(source),binary_sha256=q.sha(root/"binary"))
            def save(p,x):p.write_text(json.dumps(x))
            save(root/"review",review)
            quote=dict(status="quoted",binary_sha256=q.sha(root/"binary"),source_sha256=q.digest(source),reserved_seconds=100)
            save(root/"quote.json",quote);save(root/"owner",owner())
            save(root/"COMPLETE.json",dict(status="quoted",quote_sha256=q.sha(root/"quote.json")))
            save(root/"status.json",dict(status="complete"));save(root/"stage-costs.json",[dict(returncode=0)])
            c=dict(study="PR457",source_files=source,python_sha256=q.sha(sys.executable),tables=str(root))
            for name in ["binary","thermal","review","owner"]:c.update({name:str(root/name),name+"_sha256":q.sha(root/name)})
            c.update(calibration=str(root/"quote.json"),calibration_sha256=q.sha(root/"quote.json"))
            with patch.object(q,"manifest",return_value=source),patch.object(q,"TABLES",{"table":q.sha(root/"table")}):
                q.validate(c,main=True)
                (root/"failure.json").write_text('{}')
                with self.assertRaisesRegex(ValueError,"settle"):q.validate(c,main=True)
                (root/"failure.json").unlink()
                review["reviewer"]="";save(root/"review",review);c["review_sha256"]=q.sha(root/"review")
                with self.assertRaisesRegex(ValueError,"review"):q.validate(c,main=True)


if __name__=="__main__":unittest.main()
