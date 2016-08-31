#!/usr/bin/env python
import sys, os, pwd, grp, signal, time
from resource_management import *
from subprocess import call
from hue_service import hue_service
from configure_others_service import configureOtherService

class HueServer(Script):
  """
  Contains the interface definitions for methods like install, 
  start, stop, status, etc. for the Hue Server
  """

  def install(self, env):
    # Import properties defined in -config.xml file from params class
    import params
    env.set_params(params)
    self.install_packages(env)

    try: grp.getgrnam(params.hue_group)
    except KeyError: Group(group_name=params.hue_group)     
    try: pwd.getpwnam(params.hue_user)
    except KeyError: User(username=params.hue_user, 
                          gid=params.hue_group, 
                          groups=[params.hue_group], 
                          ignore_failures=True)  

    Directory([params.hue_log_dir, params.hue_pid_dir],
              mode=0755,
              cd_access='a',
              owner=params.hue_user,
              group=params.hue_group,
      )
    File(params.hue_log,
            mode=0644,
            owner=params.hue_user,
            group=params.hue_group,
            content=''
      )
    Execute('cd {0}; rm -rf hue*'.format(params.hue_install_dir))
    # Execute('yum -y install hue')
    Execute('cd ' + params.hue_install_dir + '; cat /etc/yum.repos.d/HD.repo | grep "baseurl" | awk -F \'=\' \'{print $2"hue/hue-3.9.0.tgz"}\' | xargs wget -O hue.tgz -a ' + params.hue_log)
    Execute('cd {0}; tar -zxvf hue.tgz; rm -rf hue.tgz'.format(params.hue_install_dir))
    Execute('ln -s {0}/desktop/libs/hadoop/java-lib/hue-plugins-{1}-SNAPSHOT.jar /usr/hdp/current/hadoop-client/lib'.format(params.hue_dir,params.hue_version))
    Execute('ln -s {0} /usr/hdp/current/hue-server'.format(params.hue_dir))
    if params.hue_bin_dir == 'UNDEFINED':
      Logger.info("Error: Hue_bin is undefined")
    # Ensure all Hue files owned by hue
    Execute('chown -R {0}:{1} {2}'.format(params.hue_user,params.hue_group,params.hue_dir))
    Execute('find {0} -iname "*.sh" | xargs chmod +x'.format(params.service_packagedir))
    # Setup hue
    # Form command to invoke setup_hue.sh with its arguments and execute it
    Execute('{0}/scripts/setup_hue.sh {1} {2} >> {3}'.format(params.service_packagedir, params.hue_dir,params.hue_user, params.hue_log))
    Logger.info("Hue_installation is completed")

  def configure(self, env):
    import params
    env.set_params(params)

    Directory(params.hue_tmp_conf,
          mode=0755,
          cd_access='a',
          owner=params.hue_user,
          group=params.hue_group,
      )
    File(params.hue_conf_file,
      action = "delete",
      owner=params.hue_user
      )
    log_content=InlineTemplate(params.hue_log_content) 
    File(format("{hue_conf}/log.conf"), 
      content=log_content, 
      owner=params.hue_user
      ) 
    # Write content field to hue confiuration file
    desktop_content=InlineTemplate(params.hue_desktop_content)
    File(format("{hue_tmp_conf}/hue.desktop.tmp.ini"), 
      content=desktop_content, 
      owner=params.hue_user
      )
    hadoop_content=InlineTemplate(params.hue_hadoop_content)
    File(format("{hue_tmp_conf}/hue.hadoop.tmp.ini"), 
      content=hadoop_content, 
      owner=params.hue_user
      )
    hive_content=InlineTemplate(params.hue_hive_content)
    File(format("{hue_tmp_conf}/hue.hive.tmp.ini"), 
      content=hive_content, 
      owner=params.hue_user
      )
    spark_content=InlineTemplate(params.hue_spark_content)
    File(format("{hue_tmp_conf}/hue.spark.tmp.ini"), 
      content=spark_content, 
      owner=params.hue_user
      )
    oozie_content=InlineTemplate(params.hue_oozie_content)
    File(format("{hue_tmp_conf}/hue.oozie.tmp.ini"), 
      content=oozie_content, 
      owner=params.hue_user
      )
    pig_content=InlineTemplate(params.hue_pig_content)
    File(format("{hue_tmp_conf}/hue.pig.tmp.ini"), 
      content=pig_content, 
      owner=params.hue_user
      )
    hbase_content=InlineTemplate(params.hue_hbase_content)
    File(format("{hue_tmp_conf}/hue.hbase.tmp.ini"), 
      content=hbase_content, 
      owner=params.hue_user
      )
    solr_content=InlineTemplate(params.hue_solr_content)
    File(format("{hue_tmp_conf}/hue.solr.tmp.ini"), 
      content=solr_content, 
      owner=params.hue_user
      )
    zookeeper_content=InlineTemplate(params.hue_zookeeper_content)
    File(format("{hue_tmp_conf}/hue.zookeeper.tmp.ini"), 
      content=zookeeper_content, 
      owner=params.hue_user
      )
    rdbms_content=InlineTemplate(params.hue_rdbms_content)
    File(format("{hue_tmp_conf}/hue.rdbms.tmp.ini"), 
      content=rdbms_content, 
      owner=params.hue_user
      )  
    Execute (format("cat {hue_tmp_conf}/hue.*.tmp.ini >> {hue_conf_file}"), user=params.hue_user) 
    
  # Call start.sh to start the service
  def start(self, env):
    import params
    import status_params
    env.set_params(params)
    self.configure(env)
    self.stop(env)
    File(status_params.hue_server_pidfile,
      mode=0644,
      owner=params.hue_user,
      group=params.hue_group,
      content=''
    )
    Execute(format("{hue_bin_dir}/supervisor >> {hue_log} 2>&1 &"), user=params.hue_user)
    Execute('ps -ef | grep hue | grep supervisor | grep -v grep | awk \'{print $2}\' > ' + status_params.hue_server_pidfile, user=params.hue_user)

  def stop(self, env):
    import params
    import status_params
    env.set_params(params)
    # Kill the process of Hue
    Execute ('ps -ef | grep hue | grep -v grep | grep -v livy | awk  \'{print $2}\' | xargs kill -9', user=params.hue_user, ignore_failures=True)
    File(status_params.hue_server_pidfile,
      action = "delete",
      owner = params.hue_user
    )

  #Called to get status of the Hue service using the pidfile
  def status(self, env):
    import status_params
    env.set_params(status_params)
    #use built-in method to check status using pidfile
    check_process_status(status_params.hue_server_pidfile)

  def usersync(self, env):
    import params
    env.set_params(params)
    Execute (format("{hue_bin_dir}/hue useradmin_sync_with_unix"), user=params.hue_user)
    
  def databasesync(self, env):
    import params
    env.set_params(params)
    Execute (format("{hue_bin_dir}/hue syncdb --noinput"), user=params.hue_user)
    Execute (format("{hue_bin_dir}/hue migrate"), user=params.hue_user)

  #Called to add configurations to other service
  def addconfigurations(self, env):
    import params
    env.set_params(params)
    if_ranger = params.has_ranger_admin
    security = params.security_enabled
    configureOtherService(if_ranger, security)

if __name__ == "__main__":
  HueServer().execute()
