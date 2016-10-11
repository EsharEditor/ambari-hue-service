#!/usr/bin/env python
import sys, os, pwd, grp, signal, time
from resource_management import *
from subprocess import call

def setup_hue():
    import params
    import status_params
    # create the pid and log dirs
    Directory([params.hue_log_dir, params.hue_pid_dir],
              mode=0755,
              cd_access='a',
              owner=params.hue_user,
              group=params.hue_group,
              create_parents=True,
      )
    File(params.hue_log_file,
      mode=0644,
      owner=params.hue_user,
      group=params.hue_group,
      content=''
    )
    Execute('cd ' + params.hue_install_dir + '; cat /etc/yum.repos.d/HDP.repo | grep "baseurl" | awk -F \'=\' \'{print $2"hue/hue-3.11.0.tgz"}\' | xargs wget -O hue.tgz -a ' + params.hue_log_file)
    Execute('cd {0}; tar -zxvf hue.tgz; rm -rf hue.tgz'.format(params.hue_install_dir))

    Execute('ln -s {0}/desktop/libs/hadoop/java-lib/hue-plugins-3.11.0-SNAPSHOT.jar /usr/hdp/current/hadoop-client/lib'.format(params.hue_dir))
    Execute('ln -s {0} /usr/hdp/current/hue-server'.format(params.hue_dir))
    # Ensure all Hue files owned by hue
    Execute('chown -R {0}:{1} {2}'.format(params.hue_user,params.hue_group,params.hue_dir))
    Execute('find {0} -iname "*.sh" | xargs chmod +x'.format(params.service_packagedir))
    # Setup hue
    # Form command to invoke setup_hue.sh with its arguments and execute it
    Execute('{0}/files/setup_hue.sh {1} {2} >> {3}'.format(params.service_packagedir, params.hue_dir,params.hue_user, params.hue_log_file))
    Logger.info("echo Hue is installed >> " + params.hue_log_file)

def configure_service(if_ranger=False, security_enabled=False): 
    import params
    import status_params
    #add configurations for services:{'configuration file1':{'key1':'value1','key2':'value2',...},
    #                                 'configuration file2':{'key1':'value1','key2':'value2',...}
    #                                 ...}
    services_configurations = {}
    services_configurations['core-site'] = {}
    services_configurations['core-site']['hadoop.proxyuser.hue.groups'] = '*'
    services_configurations['core-site']['hadoop.proxyuser.hue.hosts'] = '*'
    services_configurations['hdfs-site'] = {}
    services_configurations['hdfs-site']['dfs.namenode.acls.enabled'] = 'true'
    services_configurations['hbase-site'] = {}
    services_configurations['livy-conf'] = {}
    # add configurations
    if params.hue_hbase_module_enabled == 'Yes':
        services_configurations['core-site']['hadoop.proxyuser.hbase.groups'] = '*'
        services_configurations['core-site']['hadoop.proxyuser.hbase.hosts'] = '*'
    	if if_ranger:
    		services_configurations['hbase-site']['hbase.regionserver.thrift.http'] = 'true'
    		services_configurations['hbase-site']['hbase.thrift.support.proxyuser'] = 'true'
    if params.hue_hive_module_enabled == 'Yes':
    	services_configurations['core-site']['hadoop.proxyuser.hive.groups'] = '*'
    	services_configurations['core-site']['hadoop.proxyuser.hive.hosts'] = '*'
    	services_configurations['hive-site'] = {}
    	services_configurations['hive-site']['hive.security.authorization.sqlstd.confwhitelist.append'] = 'hive.server2.logging.operation.verbose'
    	services_configurations['webhcat-site'] = {}
    	services_configurations['webhcat-site']['webhcat.proxyuser.hue.groups'] = '*'
    	services_configurations['webhcat-site']['webhcat.proxyuser.hue.hosts'] = '*' 	
    	if if_ranger:
    		services_configurations['hive-site']['hive.server2.enable.impersonation'] = 'true'
    if params.hue_oozie_module_enabled == 'Yes':
    	services_configurations['core-site']['hadoop.proxyuser.oozie.groups'] = '*'
    	services_configurations['core-site']['hadoop.proxyuser.oozie.hosts'] = '*'
        services_configurations['oozie-site'] = {}
        services_configurations['oozie-site']['oozie.service.ProxyUserService.proxyuser.hue.groups'] = '*'
        services_configurations['oozie-site']['oozie.service.ProxyUserService.proxyuser.hue.hosts'] = '*'
    if params.hue_spark_module_enabled == 'Yes':
        services_configurations['core-site']['hadoop.proxyuser.spark.groups'] = '*'
        services_configurations['core-site']['hadoop.proxyuser.spark.hosts'] = '*'
        services_configurations['livy-conf']['livy.server.csrf_protection.enabled'] = 'false'
    if params.dfs_ha_enabled:
    	services_configurations['core-site']['hadoop.proxyuser.httpfs.groups'] = '*'
    	services_configurations['core-site']['hadoop.proxyuser.httpfs.hosts'] = '*'
    	services_configurations['httpfs-site'] = {}
    	services_configurations['httpfs-site']['httpfs.proxyuser.hue.groups'] = '*'
    	services_configurations['httpfs-site']['httpfs.proxyuser.hue.hosts'] = '*'

    if security_enabled:
    	services_configurations['core-site']['hadoop.proxyuser.HTTP.groups'] = '*'
    	services_configurations['core-site']['hadoop.proxyuser.HTTP.hosts'] = '*'
    	services_configurations['core-site']['hue.kerberos.principal.shortname'] = 'hue'
    	if params.if_hbase_exist:
    		services_configurations['hbase-site']['hbase.thrift.security.qop'] = 'auth'
    		services_configurations['hbase-site']['hbase.thrift.support.proxyuser'] = 'true'
    		services_configurations['hbase-site']['hbase.regionserver.thrift.http'] = 'true'
    		services_configurations['hbase-site']['hbase.thrift.kerberos.principal'] = params.HTTP_principal
    		services_configurations['hbase-site']['hbase.thrift.keytab.file'] = params.HTTP_keytab
    		services_configurations['hbase-site']['hbase.rpc.engine'] = 'org.apache.hadoop.hbase.ipc.SecureRpcEngine'

    # configure
    if isinstance(services_configurations,dict):
        for i in range(len(services_configurations)):
                key1 = services_configurations.keys()[i]
                value1 =services_configurations[key1]
                if isinstance(value1,dict):
                        for j in range(len(value1)):
                                key2 = value1.keys()[j]
                                value2 = value1[key2]
                                #/var/lib/ambari-server/resources/scripts/configs.sh -u admin -p admin set ambari-server-host cluster_name core-site "hadoop.proxyuser.hbase.hosts" "*"
                                cmd = format(params.service_packagedir + "/files/configs.sh set " + params.ambari_server_hostname + " " + params.cluster_name + " " + key1 + " '" + key2 + "' '"+ value2 + "'")
                                Execute(cmd)

    
    	

