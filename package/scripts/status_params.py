#!/usr/bin/env python
from resource_management import *

config = Script.get_config()

hue_pid_dir = config['configurations']['hue-env']['hue.pid.dir']
hue_server_pidfile = format("{hue_pid_dir}/hue-server.pid")
hue_livyserver_pidfile = format("{hue_pid_dir}/hue-livy_server.pid")