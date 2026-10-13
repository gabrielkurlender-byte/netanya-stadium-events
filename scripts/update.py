"""Best-effort public IFA schedule import. Fail closed if the layout changes."""
import json, re, urllib.request
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
URLS=[
 'https://www.football.org.il/team-details/team-games/?season_id=28&team_id=1068',
 'https://www.football.org.il/team-details/team-games/?season_id=28&team_id=1064',
]
class Rows(HTMLParser):
 def __init__(self): super().__init__(); self.depth=0; self.parts=[]; self.rows=[]
 def handle_starttag(self,tag,attrs):
  if tag=='tr':
   if self.depth==0:self.parts=[]
   self.depth+=1
 def handle_endtag(self,tag):
  if tag=='tr' and self.depth:
   self.depth-=1
   if not self.depth:self.rows.append(' '.join(self.parts))
 def handle_data(self,data):
  if self.depth and data.strip():self.parts.append(data.strip())
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; NetanyaEventsCalendar/1.0)'})
 with urllib.request.urlopen(req,timeout=25) as res:return res.read().decode('utf-8','replace')
def parse(url):
 parser=Rows();parser.feed(fetch(url));result=[]
 for row in parser.rows:
  row=' '.join(row.split())
  if not re.search(r'(?:אצטדיון מרים|נתניה אצטדיון מרים)',row):continue
  dt=re.search(r'(?<!\d)(\d{2})/(\d{2})/(20\d{2})(?!\d)',row)
  tm=re.search(r'(?<!\d)([01]\d|2[0-3]):[0-5]\d(?!\d)',row)
  if not dt or not tm:continue
  day,month,year=map(int,dt.groups())
  try:daydate=date(year,month,day)
  except ValueError:continue
  if daydate<date.today() or tm.group()=='00:00':continue
  title=re.search(r'([^\s].*?\s+-\s+.*?)\s+(?:נתניה\s+)?אצטדיון\s+מרים',row)
  if not title:continue
  name=title.group(1)
  name=re.sub(r'^.*?\d{2}/\d{2}/20\d{2}\s*','',name).strip()
  if len(name)>130 or len(name)<5:continue
  result.append({'title':name,'date':f'{year:04}-{month:02}-{day:02}T{tm.group()}:00+03:00','type':'כדורגל','source':url})
 return result

def main():
 events=[];success=0
 for url in URLS:
  try:
   entries=parse(url);print(url,len(entries));events+=entries;success+=1
  except Exception as e:print('SOURCE FAILED:',url,str(e))
 if not success:raise SystemExit('No sources available; preserving existing data')
 manual=json.loads((ROOT/'manual-events.json').read_text(encoding='utf-8')).get('events',[])
 events+=manual
 unique={}
 for e in events:
  if not all(e.get(k) for k in ('title','date','source')):continue
  if e['date'][:10]<date.today().isoformat():continue
  key=(e['title'].strip(),e['date'][:16]);unique[key]=e
 out={'updated':datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%d/%m/%Y %H:%M'), 'events':sorted(unique.values(),key=lambda x:x['date'])}
 # Don't erase previous events if a site silently changes layout.
 previous=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
 if not events and previous.get('events'):raise SystemExit('No events extracted; preserving existing data')
 (ROOT/'events.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Saved',len(out['events']),'events')
if __name__=='__main__':main()

