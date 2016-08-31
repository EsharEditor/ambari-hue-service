#!/usr/bin/env python
from resource_management import *

def hue_service(name=None, searchingName=None, action=None): 
    
  import params
  role = name
  processName = searchingName
  cmd = format("{hue_bin_dir}/hue")
  pid_file = format("{hue_pid_dir}/hue-{role}.pid")
  File(pid_file,
      mode=0644,
      owner=params.hue_user,
      group=params.hue_group,
      content=''
  )
  if action == 'start':
    daemon_cmd = format("{cmd} {role} &")
    Execute(daemon_cmd, user = params.hue_user)
    Execute('ps -ef | grep hue | grep -v grep | grep ' + processName + ' | awk  \'{print $2}\' > ' + pid_file, user = params.hue_user)
    
  elif action == 'stop':       
    Execute (format("cat {pid_file} | xargs kill -9"), user=params.hue_user, ignore_failures=True)
    File(pid_file,
        action = "delete",
        owner=params.hue_user
    )
