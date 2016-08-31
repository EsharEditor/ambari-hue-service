#!/usr/bin/env python
import sys, os
from resource_management import *
from hue_service import hue_service
from subprocess import call

SERVICE_NAME = "livy_server"

class LivyServer(Script):

  """
  Contains the interface definitions for methods like install, 
  start, stop, status, etc. for the Livy Server
  """

  def install(self, env):
    import params
    env.set_params(params)
    self.configure(env)
    Logger.info("Livy Server installation is completed")

  def configure(self, env):
    import params
    env.set_params(params)
    Logger.info("Livy Server configuration is completed")

  def start(self, env):
    import params
    env.set_params(params)
    self.configure(env)
    Execute('ps -ef | grep hue | grep livy | grep -v grep | awk  \'{print $2}\' | xargs kill -9', user=params.hue_user, ignore_failures=True)
    hue_service(SERVICE_NAME, 'livy', action = 'start')

  def stop(self, env):
    import params
    env.set_params(params)
    hue_service(SERVICE_NAME, 'livy',  action = 'stop')

  #Called to get status of the Livy server using the pidfile
  def status(self, env):
    import status_params
    env.set_params(status_params)
    #use built-in method to check status using pidfile
    check_process_status(status_params.hue_livyserver_pidfile)

if __name__ == "__main__":
  LivyServer().execute()