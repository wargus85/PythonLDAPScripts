# Python LDAP 3 Scripts

## Purpose
I wrote these, and some other unpublished scripts to help me identify the users of Linux systems, which needs further explanation: In the corporate environments I work in, Active Directory has been the source of truth for identity and access management (IAM). So in order to notify users that systems are being patched it is important to refer to the source of truth and not an arbitrary flat inventory file which may or may not reflect the actual users of a system.

That's where these scripts come in. The report_single_user script looks up an AD user and reports back useful attributes. The email_script looks up an AD Group, based on the name of a server (following a set convention) and then emails the members of that group.

## Are they any good?
They're good enough for me. Are they perfect? No, but they work well enough and it streamlines troubleshooting enough to be worth having had written them.

### But why Python?
Good question, anonymous internet person. Powershell could probably do the same thing in significantly less lines of code. But sadly, I'm rubbish at Powershell, and the last time I checked, the linux port of PWSH didn't have the AD modules. Furthermore, all my inventory files and ansible roles exist on a Linux server. So do what you know, and I know python.

### Why Publish them?
I couldn't find anything like this online myself, so thought that other sysadmins might benefit from them.

## Requirements
Read the Pipfile in this directory.

## Installation

Personally I use pipenv on Linux. The requirements are in the pipfile.

```bash
git clone https://github.com/wargus85/PythonLDAPScripts
cd PythonLDAPScripts
pipenv shell
pipenv install
```
However you can not use pipenv and just install the system python packages you need.

## Usage
**Read the code before you use it!** The scripts will take the ldap search base and server to query as an input, however its easier if you're working in a single AD environment to just add a default search base and server to talk to.

### email_script.py
NB: I use ansible inventory files, so read the ansible documentation for the correct way to write yaml files.
Additionally, some servers or groups of servers are not in AD by design. For those exceptions I have an override bool variable which the script will look for. See the example_inventory for more information. 

```bash
(PythonLDAPScripts) wargus@woztop:~/projects/PythonLDAPScripts/scripts$ ./email_script.py --help
usage: email_script.py [-h] --inventory INVENTORY [--run] --username USERNAME --date DATE [--server SERVER] [--searchbase SEARCHBASE]

Script to process usernames from a yaml inventory file. See the readme for more information.By DEFAULT the program will not email everyone, but do a dry run. Specify the appropriate flag to actually email people

options:
  -h, --help            show this help message and exit
  --inventory INVENTORY, -i INVENTORY
                        the path to the inventory file
  --run, -r             Process and email everyone, default is to do a dry run
  --username USERNAME, -u USERNAME
                        username for AD bind, fqdn not required
  --date DATE, -d DATE  The date of the server patching, eg: '21st March 2021'
  --server SERVER, -s SERVER
                        AD/LDAP Server to connect to with FQDN
  --searchbase SEARCHBASE, -b SEARCHBASE
                        AD/LDAP search base. Setting this will override the default. EG: 'OU=Everything,dc=domain,dc=company,dc=com'
```

### report_single_user.py

The report_single_user.py script does just what it says on the box. It will look for and return information about users. You can specify as many users as you like, and it will iterate through all the returned results. It will also respect the '*' character. For instance:
```bash
./report_single_user --username admin "JoeBlogs" "A*"
```
will return all results that start with A or match exactly JoeBlogs.

```bash
(PythonLDAPScripts) wargus@woztop:~/projects/PythonLDAPScripts/scripts$ ./email_script.py --help
usage: email_script.py [-h] --inventory INVENTORY [--run] --username USERNAME --date DATE [--server SERVER] [--searchbase SEARCHBASE]

Script to process usernames from a yaml inventory file. See the readme for more information.By DEFAULT the program will not email everyone, but do a dry run. Specify the appropriate flag to actually email people

options:
  -h, --help            show this help message and exit
  --inventory INVENTORY, -i INVENTORY
(PythonLDAPScripts) wargus@woztop:~/projects/PythonLDAPScripts/scripts$ ./report_single_user.py --help
usage: report_single_user.py [-h] --username USERNAME [--server SERVER] [--searchbase SEARCHBASE] users [users ...]

Script to search AD for users, it will report back all their AD group memberships.

positional arguments:
  users                 User/s to search for in ad, in the format of either 'Full Name' in quotes, or shortname, without

options:
  -h, --help            show this help message and exit
  --username USERNAME, -u USERNAME
                        username for AD bind, fqdn not required
  --server SERVER, -s SERVER
                        AD/LDAP Server to connect to with FQDN
  --searchbase SEARCHBASE, -b SEARCHBASE
                        AD/LDAP search base. Setting this will override the default. EG: 'OU=Everything,dc=domain,dc=company,dc=com'
```