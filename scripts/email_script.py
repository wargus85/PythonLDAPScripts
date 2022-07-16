#!/usr/bin/env python
# https://ldap3.readthedocs.io/en/latest/tutorial_intro.html#accessing-an-ldap-server

# By Warren Argus
# This script will email the users of a VM based solely on the name of the VM and its associate security group.
# In my current organisation, the 
# If the user is disabled, it wont email them, but instead print a friendly message
#  
# It will also check that the inventory variable on the host: override has been set to either True or False,
# If True, it will then look for a manually entered list of users. The same is true if a group override variable
# has been set. Hopefully the individual variable should NEVER be set, although on non-AD joined Linux VMs, this
# will be the case.
#
# The Group Variable will only be set on VMs that are a group, that is, owned and managed by their own team.
# The Research Support and Innovation (RSI) team, are the only example of this at the institute.

import getpass, argparse, yaml, smtplib
from ldap3 import Server, Connection, ALL, NTLM

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

parser = argparse.ArgumentParser(description="Script to process usernames from a yaml inventory file. See the readme for more information.By DEFAULT the program will not email everyone, but do a dry run. Specify the appropriate flag to actually email people")
parser.add_argument("--inventory","-i", type=str,help="the path to the inventory file",required=True)
parser.add_argument("--run","-r",help="Process and email everyone, default is to do a dry run",required=False,default=False,action='store_true')
parser.add_argument("--username","-u", type=str,help="username for AD bind, fqdn not required",required=True)
parser.add_argument("--date",'-d',type=str,help="The date of the server patching, eg: '21st March 2021'",required=True)
parser.add_argument("--server","-s", type=str,help="AD/LDAP Server to connect to with FQDN",required=False)
parser.add_argument("--searchbase","-b", type=str,help="AD/LDAP search base. Setting this will override the default. EG: 'OU=Everything,dc=domain,dc=company,dc=com'",required=False)

args = parser.parse_args()

longdate = args.date

my_pass = getpass.getpass(prompt='Enter your AD password: ')
my_username = "domain\\"+args.username

#Setup the defaults.
if not args.server:
    ServerFQDN = 'adserver.domain.com.au'
else:
    ServerFQDN = args.server

if not args.searchbase:
    SearchBase = 'dc=your,dc=domain,dc=com,dc=au'
else:
    ServerFQDN = args.searchbase

# The try opening the file
try:
    with open(args.inventory,'r') as stream:
        InventoryFile = yaml.load(stream,Loader=yaml.FullLoader)
except:
    print('Something is wrong with the inventory file')
    exit()
#generate the hostnames
hosts = InventoryFile['all']['hosts'].keys()

#Setup the connection to the server
server = Server(ServerFQDN,use_ssl=True, get_info=ALL)
conn = Connection(server,user=my_username,password=my_pass, authentication=NTLM, auto_bind=True)

#define the ldap search

def LdapUserSearch(UserName):
    user = {}
    if UserName[:3] == "CN=": 
        FilterString="(objectclass=person)"
        conn.search(UserName,search_filter=FilterString,attributes=['distinguishedname','memberOf','mail','displayName','givenName','sAMAccountName','title','userAccountControl'])
    else:
        FilterString = "(sAMAccountName="+UserName+")"
        conn.search(SearchBase,FilterString,attributes=['distinguishedname','memberOf','mail','displayName','givenName','sAMAccountName','title','userAccountControl'])

    user['dn'] = conn.entries[0].distinguishedname.value
    if conn.entries[0].mail.value is None:
        user['email'] = False
    else:
        user['email'] = conn.entries[0].mail.value
    # user['groups'] = conn.entries[0].memberOf
    user['full_name'] = conn.entries[0].displayName.value
    user['firstname'] = conn.entries[0].givenName.value
    user['accname'] = conn.entries[0].sAMAccountName.value
    user['title'] = conn.entries[0].title.value
    if conn.entries[0].userAccountControl.value == 514:
        user['active'] = False
    else: 
        user['active'] = True
    return user


def GroupSearch(ServerName):
    #Modify the search string to suite your organisation.
    searchString='(&(objectClass=group)(cn='+"security_"+ServerName+"_Access"+'))'
    try:
        conn.search(search_base=SearchBase,search_filter=searchString, search_scope='SUBTREE',attributes = ['member'])
        return conn.entries[0]['member']
    except IndexError:
        return {}

def EmailUser(GivenName,EmailAddress,ServerList,MyName,MyEmail,MyTitle):

    me = "noreply@your.domain.com.au"
    you = EmailAddress
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "[DO NOT REPLY] Server Patching "+longdate
    msg['From'] = me
    msg['To'] = you
    html = """\
    <html>
    <head></head>
    <body>
        <p>Hi """+GivenName+""",</p>
    <p>You are a registered user of the system/s <b>"""+ServerList+"""</b> which is/are scheduled to be patched and rebooted <b>Thursday """+longdate+""".</b></p>
    <p>If you have access to the Vcenter environment, <b>please ensure that your virtual machine/s are turned on during this time.</b></p>
    <p>Make sure that any running processes have completed or have been stopped before patching. Please also close any sessions and log off.</p>
    <p>Patching will commence at 7:30PM and finish by midnight. During this time the server will be rebooted.</p>
    <p>Patching is a critical process that ensures your system remains secure with up to date software. It is important that this process be undertaken regularly to protect against new vulnerabilities. If the system cannot be rebooted this time, please contact me directly or raise a service ticket to arrange a more suitable time.</p>
    <p>On Friday morning please check that your system is working and you can access your network drives. If you experience any problems please reach out to the service desk.</p>
    <p>Kind regards,</p>
    <p>"""+MyName+"""<br />"""+MyTitle+"""<br /><a href="mailto:"""+MyEmail+"""">"""+MyEmail+"""</a></p>
    </body>
    </html>
    """
    part2 = MIMEText(html, 'html')
    msg.attach(part2)
    # Enter your server's IP address. THis script assumes that the server will accept all incoming mail, eg its an open relay.
    s = smtplib.SMTP('10.0.0.1')
    s.sendmail(me, you, msg.as_string())
    s.quit()

#get the details of the admin sending the emails to populate the email
SendingAdmin = LdapUserSearch(args.username)

UserList = {}
HostList = {}

for host in InventoryFile['all']['hosts']:
    try:
        #check if there is an override variable set on the individual host
        OverrideVar = InventoryFile['all']['hosts'][host]['override']
    except:
        OverrideVar = False

    try:
        #check if there is an override variable set on the inventory level
        GrpOverrideVar = InventoryFile['all']['vars']['override']
    except:
        GrpOverrideVar = False

    # check for override variables
    # if the override variable is there, use the userlist to email people
    # instead of looking up group membership.
    # Once the check are done, then set the list of users appropriately 
    if OverrideVar is True:
        HostUsers = InventoryFile['all']['hosts'][host]['machine_users']
    
    if OverrideVar is False:
        HostUsers = GroupSearch(host)  

    if GrpOverrideVar == True:
        HostUsers = InventoryFile['all']['vars']['machine_users']

    # create a new dictionary entry in the HostList dict, with the name of the server as the index var
    # and then create a users index with an empty list
    HostList[host] = {'users':[]}

    for user in HostUsers:
        #lookup the user for the current host and then add them to the 
        # host's userlist.
        CurrentUser =  LdapUserSearch(user)
        HostList[host]['users'].append(CurrentUser)

# Now we have a list of servers with the users, we need to reverse that, so we have a list of users and their servers.
# This is so we can group email messages together.

# print(HostList)

#create the structure
for host in HostList:
    for user in HostList[host]['users']:
        #initialise the user
        UserList[user['email']] = {'servers':[]}

# print(HostList)

#populate the data
for host in HostList:
    for user in HostList[host]['users']:
        UserList[user['email']]['servers'].append(host)
        UserList[user['email']]['details'] = {'gn':user['firstname'],'active':user['active']}

if args.run is True:
    for user in UserList.items():
        if user[0] is False:
            print ("error in group config: "+host)
            print(user)
        else:
            email = user[0]
            FirstName = UserList[user[0]]['details']['gn']
            ServerStr = str(UserList[user[0]]['servers'].pop())
            while len(UserList[user[0]]['servers']) > 0:
                ServerStr = ServerStr + ", " +str(UserList[user[0]]['servers'].pop())
        
            if UserList[user[0]]['details']['active'] is not False:
                EmailUser(FirstName,email,ServerStr,SendingAdmin['full_name'],SendingAdmin['email'],SendingAdmin['title'])
                print("Emailing User: "+email+", Servers: "+ServerStr)

            else:
                print("DISABLED USER: "+"email")

if args.run is False:
    for user in UserList.items():
        if user[0] is False:
            print ("error in group config: "+host)
            print(user)
        else:
            email = user[0]
            ServerStr = str(UserList[user[0]]['servers'].pop())
            while len(UserList[user[0]]['servers']) > 0:
                ServerStr = ServerStr + ", " +str(UserList[user[0]]['servers'].pop())
            print("NOT Emailing User: "+email+", Servers: "+ServerStr)

