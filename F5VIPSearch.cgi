#!python

'''
  Author: Ricky Martinez
  Task:   Obtains information from the database to be displayed on the VIP Search tool
          It obtains:
            Hostname, Virtual IP, Virtual Server Name, Virtual Port, Pool IP, Pool Name from
            F5_stat
            Internet NAT from NATedIP
            DealerNAT from DealerRouterNAT
            DNS from ARPTable

          Sends information to the template F5VIPSearch.html
'''

import jinja2
import cgi
import cgitb
import MySQLdb
import datetime
import collections
import pprint

###############
DEBUG_LIST = []
###############

cgitb.enable();
templates = jinja2.Environment(loader = jinja2.FileSystemLoader(searchpath="templates"))

debug_list = []

def IsDefined(search_dict):
  if any(search_dict.values()):
      return True
  else:
      return False

#PROCESS time
now = datetime.datetime.now()
locale = "pm"
hour = now.hour
if hour >=5 and hour< 18:
    locale = "am"

#GET DB infor
with open('pythonmysql.ini','r') as f:
  lines = f.readlines()
  for i, line in enumerate(lines):
    if i == 0:
      host = line[:-1]
    elif i == 1:
      username = line[:-1]
    elif i == 2:
      password = line[:-1]
    elif i == 3:
      socket = line[:-1]

db = MySQLdb.connect(host=host, user=username, passwd = password, db = "NMG", unix_socket=socket)
cur = db.cursor()

#INTANTIATE
result = {}
search_criteria = {}
query = "SELECT VIP_IP,VIP_Name,VIP_Port,MemberIP,MemberName,Hostname FROM F5_Stat WHERE 1=1 AND Hostname NOT LIKE '%-02' and DATE(timestamp) = CURDATE()"

#GET IP Address entered
form = cgi.FieldStorage()
vServer_ip_search = form.getfirst("vServer_ip", False)
vServer_name_search = form.getfirst("vServer_name", False)
vServer_port_search = form.getfirst("vServer_port", False)
member_ip_search = form.getfirst("member_ip", False)
member_name_search = form.getfirst("member_name", False)

search_criteria['VIP_Name'] = vServer_name_search
search_criteria['VIP_IP'] = vServer_ip_search
search_criteria['VIP_Port'] = vServer_port_search
search_criteria['MemberIP'] = member_ip_search
search_criteria['MemberName'] = member_name_search

#CHECK if there is a search
dNAT_res = ''
dNAT_query = ''
DNS = ''
res = []
##WORKAROUND: Router configs display US and EU DealerNATs
dNATs = []
#If there is a search
is_search = IsDefined(search_criteria);
if is_search:
  #BUILD QUERY
  for key,val in search_criteria.iteritems():
    if search_criteria[key]:
      query += " AND " + key + ' LIKE "' + val + '"'
  query += " ORDER BY VIP_IP ASC"
  debug_list.append(query)
  cur.execute(query)
  res = cur.fetchall()


##PARSES query data
for info in res:
  vServer_ip = info[0]
  vServer_name = info[1]
  vServer_port = info[2]
  member_ip = info[3]
  member_name = info[4]
  hostname = info[5]

  ##RESOLVE Internet/Dealer NATs
  iNAT_query = "SELECT NATedIP from InternetNATs where SourceIP = '"+ vServer_ip +"'"
  cur.execute(iNAT_query)
  iNAT_res = cur.fetchall()


  for iNAT_info in iNAT_res:
    iNAT = iNAT_info[0]

  ##WORKAROUND: Router configs return US and EU DealerNATs
  dNAT_query = "SELECT NATedIP from DealerRouterNATs where SourceIP = '" +vServer_ip+ "'"
  dNAT_count = cur.execute(dNAT_query)
  if dNAT_count>0:
    dNAT_res = cur.fetchall()
    dNAT_res = dNAT_res[0];
  else:
    dNAT_res = "None";


  ##RESOLVE DNS
  dns_query = "SELECT dns from ARPTable WHERE ip = '"+member_ip+"'"
  DEBUG_LIST.append(dns_query)
  cur.execute(dns_query)
  dns_res = cur.fetchall()
  for dns_info in dns_res:
    DNS = dns_info[0]
  if DNS == "NULL":
    DNS = "None"

  if not "data" in result:
    result["data"] = []
  result["data"].append({
    "hostname"          :   hostname,
    "vServer_ip"        :   vServer_ip,
    "vServer_name"      :   vServer_name,
    "vServer_port"      :   vServer_port,
    "member_ip"         :   member_ip,
    "member_name"       :   member_name,
    "iNAT"              :   iNAT_res,
    "dNAT"              :   dNAT_res,
    "DNS"               :   DNS,
  })

template = templates.get_template("F5VIPSearch.html")
print(template.render(result=result, debug_list=debug_list,is_search=is_search, DEBUG_LIST=DEBUG_LIST))
