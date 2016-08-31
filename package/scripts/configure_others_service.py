#!/usr/bin/env python
import sys, os, pwd, grp, signal, time
from resource_management import *

def configureOtherService(if_ranger=False,security=False): 
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
    # add configurations
    if params.if_hbase_exist:
        services_configurations['core-site']['hadoop.proxyuser.hbase.groups'] = '*'
        services_configurations['core-site']['hadoop.proxyuser.hbase.hosts'] = '*'
    	if if_ranger:
    		services_configurations['hbase-site']['hbase.regionserver.thrift.http'] = 'true'
    		services_configurations['hbase-site']['hbase.thrift.support.proxyuser'] = 'true'
    if params.if_hive_exist:
    	services_configurations['core-site']['hadoop.proxyuser.hive.groups'] = '*'
    	services_configurations['core-site']['hadoop.proxyuser.hive.hosts'] = '*'
    	services_configurations['hive-site'] = {}
    	services_configurations['hive-site']['hive.security.authorization.sqlstd.confwhitelist.append'] = 'hive.server2.logging.operation.verbose'
    	services_configurations['webhcat-site'] = {}
    	services_configurations['webhcat-site']['webhcat.proxyuser.hue.groups'] = '*'
    	services_configurations['webhcat-site']['webhcat.proxyuser.hue.hosts'] = '*' 	
    	if if_ranger:
    		services_configurations['hive-site']['hive.server2.enable.impersonation'] = 'true'
    if params.if_oozie_exist:
    	services_configurations['core-site']['hadoop.proxyuser.oozie.groups'] = '*'
    	services_configurations['core-site']['hadoop.proxyuser.oozie.hosts'] = '*'
        services_configurations['oozie-site'] = {}
        services_configurations['oozie-site']['oozie.service.ProxyUserService.proxyuser.hue.groups'] = '*'
        services_configurations['oozie-site']['oozie.service.ProxyUserService.proxyuser.hue.hosts'] = '*'
    if params.if_spark_exist:
        services_configurations['core-site']['hadoop.proxyuser.spark.groups'] = '*'
        services_configurations['core-site']['hadoop.proxyuser.spark.hosts'] = '*'
    if params.dfs_ha_enabled:
    	services_configurations['core-site']['hadoop.proxyuser.httpfs.groups'] = '*'
    	services_configurations['core-site']['hadoop.proxyuser.httpfs.hosts'] = '*'
    	services_configurations['httpfs-site'] = {}
    	services_configurations['httpfs-site']['httpfs.proxyuser.hue.groups'] = '*'
    	services_configurations['httpfs-site']['httpfs.proxyuser.hue.hosts'] = '*'

    if security:
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
                                #/var/lib/ambari-server/resources/scripts/configs.sh -u admin -p admin set ambari-server-host cluster_name core-site "hadoop_aaa" "123456"
                                #cmd = format(params.service_packagedir + "/scripts/configs.sh -u " + params.ambari_user + " -p " + params.ambari_user_password + " set " + params.ambari_server_host + " " + params.cluster_name + " " + key1 + " " + key2 + " "+ value2)
                                cmd = format(params.service_packagedir + "/scripts/configs.sh set " + params.ambari_server_host + " " + params.cluster_name + " " + key1 + " '" + key2 + "' '"+ value2 + "'")
                                Execute(cmd)

    
    	

