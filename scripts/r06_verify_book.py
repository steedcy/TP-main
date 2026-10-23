import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path.home()/"Documents/Codex/TIP-prep-deps"))
import xlrd
ROOT=pathlib.Path(__file__).resolve().parents[1]
before=ROOT/"document/正式测试用例V2-执行结果.pre-R06-20261023.xls"
after=ROOT/"document/正式测试用例V2-执行结果.xls"
a=xlrd.open_workbook(str(before),formatting_info=True);b=xlrd.open_workbook(str(after),formatting_info=True)
targets=[35,36,37,41,45,46,47,52,61]
allowed=set()
for n in targets:
 base=(n-1)*14
 for r in (5,6,7):allowed.add(("项目测试用例",base+r,2))
 for r in range(9,14):allowed.update({("项目测试用例",base+r,4),("项目测试用例",base+r,5)})
diffs=[];style_diffs=[]
def style(book,index):
 x=book.xf_list[index]
 def attrs(obj):return tuple(sorted((k,v) for k,v in obj.__dict__.items() if not k.startswith("_") and k not in ("xf_index",)))
 return (x.font_index,x.format_key,x.is_style,x.lotus_123_prefix,attrs(x.alignment),attrs(x.border),attrs(x.background),attrs(x.protection))
if a.sheet_names()!=b.sheet_names():raise SystemExit("worksheet names changed")
for name in a.sheet_names():
 sa,sb=a.sheet_by_name(name),b.sheet_by_name(name)
 if (sa.nrows,sa.ncols)!=(sb.nrows,sb.ncols):raise SystemExit(f"worksheet dimensions changed: {name}")
 for r in range(sa.nrows):
  for c in range(sa.ncols):
   key=(name,r,c)
   if sa.cell_value(r,c)!=sb.cell_value(r,c):
    if key not in allowed:diffs.append({"sheet":name,"row":r+1,"column":c+1,"before":sa.cell_value(r,c),"after":sb.cell_value(r,c)})
   if style(a,sa.cell_xf_index(r,c))!=style(b,sb.cell_xf_index(r,c)):style_diffs.append({"sheet":name,"row":r+1,"column":c+1,"before":sa.cell_xf_index(r,c),"after":sb.cell_xf_index(r,c)})
if diffs or style_diffs:raise SystemExit(json.dumps({"unexpectedValueDiffs":diffs[:10],"styleDiffs":style_diffs[:10]},ensure_ascii=False))
cases=b.sheet_by_name("项目测试用例")
counts={"P":0,"F":0,"NT":0,"blank":0};untouched=0
for i in range(95):
 code=f"TC-{i+1:03d}";v=str(cases.cell_value(i*14+7,2)).strip();counts[v or "blank"]+=1
 if i+1 not in targets:
  if cases.cell_value(i*14+7,2)!=a.sheet_by_name("项目测试用例").cell_value(i*14+7,2):raise SystemExit(f"unrequested result changed: {code}")
  untouched+=1
evidence={"verifiedAt":"2026-10-23","backup":str(before),"workbook":str(after),"worksheetNames":b.sheet_names(),"caseCount":95,"counts":counts,"updatedCases":[f"TC-{n:03d}" for n in targets],"unchangedOtherCases":untouched,"unexpectedValueDiffs":diffs,"styleDiffs":style_diffs,"result":"PASS"}
out=ROOT/"document/formal-test-evidence/R06-book-verification.json"
out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(evidence,ensure_ascii=False))
