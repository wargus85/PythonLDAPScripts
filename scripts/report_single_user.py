#!/usr/bin/env python3
#
# Script written by Warren Argus
# Use this script to report the AD groups that a single user is in
#
# To make your life easier, set the variable ServerFQDN to your AD/LDAP server in line 27
# And also do the same for the search base in line 32
#
#  
# run the script with the --help option to see usage summary

import getpass, argparse
from ldap3 import Server, Connection, ALL, NTLM

parser = argparse.ArgumentParser(description="Script to search AD for users, it will report back all their AD group memberships.")
parser.add_argument("--username","-u", type=str,help="username for AD bind, fqdn not required",required=True)
parser.add_argument('users',type=str,help="User/s to search for in ad, in the format of either 'Full Name' in quotes, or shortname, without",nargs='+')
parser.add_argument("--server","-s", type=str,help="AD/LDAP Server to connect to with FQDN",required=False)
parser.add_argument("--searchbase","-b", type=str,help="AD/LDAP search base. Setting this will override the default. EG: 'OU=Everything,dc=domain,dc=company,dc=com'",required=False)
args = parser.parse_args()

my_pass = getpass.getpass(prompt='Enter your AD password: ')
my_username = "domain\\"+args.username

#Setup the defaults.
if not args.server:
    ServerFQDN = 'adserver.domain.com'
else:
    ServerFQDN = args.server

if not args.searchbase:
    SearchBase = 'dc=domain,dc=com,dc=au'
else:
    ServerFQDN = args.searchbase

server = Server(ServerFQDN,use_ssl=True, get_info=ALL)
conn = Connection(server,user=my_username,password=my_pass, authentication=NTLM, auto_bind=True)

def LdapUserSearch(UserName):
    users = {}
     #create empty dictionary
    FilterString = "(|(cn="+UserName+")(sAMAccountName="+UserName+"))"
    #attempt to populate the contents of the dictionary from AD
    conn.search(SearchBase,FilterString,attributes=['distinguishedname','memberOf','mail','displayName','sAMAccountName','userAccountControl'])

    for entry in conn.entries:
        user = {}
        if entry.mail.value is None:
            user['email'] = "No Email"
        else:
            user['email'] = entry.mail.value

        user['dn'] = entry.distinguishedname.value
        user['groups'] = entry.memberOf
        user['name'] = entry.displayName.value
        user['accname'] = entry.sAMAccountName.value

        if entry.userAccountControl.value == 514:
            user['active'] = False
        else: 
            user['active'] = True

        users[user['accname']] = user
 
    return users

def LdapCNSearch(GroupName): 
    #Function that will get the nice name of a group and return it.
    searchString='(&(objectClass=group)(distinguishedName='+GroupName+'))'
    try:
        conn.search(search_base=SearchBase,search_filter=searchString,attributes=['cn'])
    except:
        return "GROUP ERROR: "+ GroupName[:50]

    return str(conn.entries[0].cn)

for user in args.users:
    #the main part. Iterates through the users in the arguments and looks them up.
    SearchResults = LdapUserSearch(user)
    ResultKeys = SearchResults.keys()

    for SingleResult in ResultKeys:
        # #check that the returned dict object isnt empty.
        UserName = SearchResults[SingleResult]['name']
        Email = SearchResults[SingleResult]['email']
        sAMAccountName = SearchResults[SingleResult]['accname']
        if sAMAccountName is None:
            sAMAccountName = "None"
        
        print("Username: "+UserName+"\t email: "+Email+"\nsAMAccountName: "+sAMAccountName)
        print("Groups:")
        #print the groups out
        for group in SearchResults[SingleResult]['groups']:
            if group is not None:
                GroupNiceName = LdapCNSearch(group)
                print("\t"+GroupNiceName)

