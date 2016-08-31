#!/usr/bin/env python
import status_params
import os
import re
from resource_management import *
from ambari_commons.os_check import OSCheck
from ambari_commons.str_utils import cbool, cint

# config object that holds the configurations declared in the -config.xml file
config = Script.get_config()
tmp_dir = Script.get_tmp_dir()
#e.g. /var/lib/ambari-agent/cache/stacks/HDP/2.3/services/HUE/package
service_packagedir = os.path.realpath(__file__).split('/scripts')[0]
hostname = config['hostname']
cluster_name = str(config['clusterName'])
ambari_server_host = default("/clusterHostInfo/ambari_server_host", [])[0]

hue_apps = ['security','pig','filebrowser','jobbrowser','zookeeper','search','rdbms','metastore','spark','beeswax','jobsub','hbase','oozie','indexer']
# Comma separated list of apps to not load at server startup.
app_blacklists = ['security','sqoop','impala']

# Configurations of security and kerberos
security_enabled = config['configurations']['cluster-env']['security_enabled']
if security_enabled:
	HTTP_principal = config['configurations']['hdfs-site']['dfs.web.authentication.kerberos.principal']
	HTTP_keytab = config['configurations']['hdfs-site']['dfs.web.authentication.kerberos.keytab']
	hue_principal = config['configurations']['hue-Desktop']['hue.kerberos.principal'].replace('_HOST',hostname.lower())
	hue_keytab = config['configurations']['hue-Desktop']['hue.kerberos.keytab']
	kinit_path = config['configurations']['hue-Desktop']['kinit.path']
	zk_principal = config['configurations']['zookeeper-env']['zookeeper_principal_name'].replace('_HOST',hostname.lower())
	zk_keytab = config['configurations']['zookeeper-env']['zookeeper_principal_name']

# Configurations of HDFS
namenode_host = default("/clusterHostInfo/namenode_host", [])
namenode_host.sort()
namenode_address = None
if 'dfs.namenode.rpc-address' in config['configurations']['hdfs-site']:
	namenode_rpcaddress = config['configurations']['hdfs-site']['dfs.namenode.rpc-address']
	namenode_address = format("hdfs://{namenode_rpcaddress}")
else:
	namenode_address = config['configurations']['core-site']['fs.defaultFS']
# To judge whether the namenode HA mode
logical_name = ''
dfs_ha_enabled = False
dfs_ha_nameservices = default("/configurations/hdfs-site/dfs.nameservices", None)
dfs_ha_namenode_ids = default(format("/configurations/hdfs-site/dfs.ha.namenodes.{dfs_ha_nameservices}"), None)
dfs_ha_namemodes_ids_list = []
if dfs_ha_namenode_ids:
	dfs_ha_namemodes_ids_list = dfs_ha_namenode_ids.split(",")
	dfs_ha_namenode_ids_array_len = len(dfs_ha_namemodes_ids_list)
	if dfs_ha_namenode_ids_array_len > 1:
		dfs_ha_enabled = True
if dfs_ha_enabled:
	# Hostname of the active and standby HDFS Namenode (only used when HA is enabled)
	dfs_ha_namenode_active = default("/configurations/hadoop-env/dfs_ha_initial_namenode_active", None)
	dfs_ha_namenode_standby = default("/configurations/hadoop-env/dfs_ha_initial_namenode_standby", None)
	namenode_address = format('hdfs://{dfs_ha_nameservices}')
	logical_name = dfs_ha_nameservices
	hdfs_httpfs_host = config['configurations']['hue-Hadoop']['HDFS.HttpFS.host']
	# if kerberos is disabled, using HttpFS . Otherwise using WebHDFS.
	if hdfs_httpfs_host in namenode_host and not security_enabled:
		webhdfs_url = format('http://' + hdfs_httpfs_host + ':14000/webhdfs/v1')
	else:
		webhdfs_url = format('http://' + hdfs_httpfs_host + ':50070/webhdfs/v1')
else:
	dfs_namenode_http_address = config['configurations']['hdfs-site']['dfs.namenode.http-address']
	webhdfs_url = format('http://' + dfs_namenode_http_address + '/webhdfs/v1')

# Configurations of Yarn
resourcemanager_hosts = default("/clusterHostInfo/rm_host", [])
resourcemanager_port = config['configurations']['yarn-site']['yarn.resourcemanager.address'].split(':')[-1]
resourcemanager_ha_enabled = False
if len(resourcemanager_hosts) > 1:
	resourcemanager_ha_enabled = True
if resourcemanager_ha_enabled:
	resourcemanager_host1 = config['configurations']['yarn-site']['yarn.resourcemanager.hostname.rm1']
	resourcemanager_host2 = config['configurations']['yarn-site']['yarn.resourcemanager.hostname.rm2']
	resourcemanager_webapp_address1 = config['configurations']['yarn-site']['yarn.resourcemanager.webapp.address.rm1']
	resourcemanager_webapp_address2 = config['configurations']['yarn-site']['yarn.resourcemanager.webapp.address.rm2']
	resourcemanager_api_url1 = format('http://{resourcemanager_webapp_address1}')
	resourcemanager_api_url2 = format('http://{resourcemanager_webapp_address2}')
	proxy_api_url1 = resourcemanager_api_url1
	proxy_api_url2 = resourcemanager_api_url2
else:
	resourcemanager_host1 = resourcemanager_hosts[0]
	resourcemanager_webapp_address1 = config['configurations']['yarn-site']['yarn.resourcemanager.webapp.address']
	resourcemanager_api_url1 = format('http://{resourcemanager_webapp_address1}')
	proxy_api_url1 = resourcemanager_api_url1
histroryserver_host = default("/clusterHostInfo/hs_host", [])
history_server_api_url = format('http://{histroryserver_host[0]}:19888')
slave_hosts = default("/clusterHostInfo/slave_hosts", [])

# Configurations of Oozie
# Pig and Jobsub service are depended on oozie in Hue
oozie_servers_hosts = default("/clusterHostInfo/oozie_server", [])
if_oozie_exist = False
if len(oozie_servers_hosts) == 0:
	app_blacklists.append('pig')
	app_blacklists.append('jobsub')
	app_blacklists.append('oozie')
else:
	if_oozie_exist = True
	oozie_url = config['configurations']['oozie-site']['oozie.base.url']

# Configurations of Solr
solr_master_hosts = default("/clusterHostInfo/solr_master_hosts", [])
solr_master_hosts.sort()
if_solr_exist = False
if len(solr_master_hosts) == 0:
	app_blacklists.append('search')
else:
	if_solr_exist = True
	solr_port = config['configurations']['solr-env']['solr.port']
	solr_znode = config['configurations']['solr-config']['solr.znode']
	solr_master_host = solr_master_hosts[0]
	solr_url = format('http://' + solr_master_host + ':' + str(solr_port) + solr_znode + '/')

# Configurations of Hive and Pig
# Hive service is depended on Pig in ambari
hive_server_hosts =  default("/clusterHostInfo/hive_server_host", [])
if_hive_exist = False
if_pig_exist = False
if len(hive_server_hosts) == 0:
	app_blacklists.append('beeswax')
	app_blacklists.append('metastore')
	app_blacklists.append('pig')
else:
	if_hive_exist = True
	if_pig_exist = True
	hive_server_host = config['clusterHostInfo']['hive_server_host'][0]
	hive_transport_mode = config['configurations']['hive-site']['hive.server2.transport.mode']
	if hive_transport_mode.lower() == "http":
  		hive_server_port = config['configurations']['hive-site']['hive.server2.thrift.http.port']
	else:
		hive_server_port = default('/configurations/hive-site/hive.server2.thrift.port',"10000")

# Configurations of Hbase
hbase_master_hosts = default("/clusterHostInfo/hbase_master_hosts", [])
hbase_clusters = []
if_hbase_exist = False
if len(hbase_master_hosts) == 0:
	app_blacklists.append('hbase')
else:
	if_hbase_exist = True
	for i in range(len(hbase_master_hosts)):
		hbase_clusters.append(format("(Cluster" + str(i+1) + "|" + hbase_master_hosts[i] + ":9090)"))
	hbase_cluster = ",".join(hbase_clusters)

# Configurations of Zookeeper
zookeeper_hosts = default("/clusterHostInfo/zookeeper_hosts", [])
zookeeper_hosts.sort()
zookeeper_client_port = default('/configurations/zoo.cfg/clientPort', None)
zookeeper_host_ports = []
if len(zookeeper_hosts) == 0:
	app_blacklists.append('zookeeper')
else:
	if zookeeper_client_port is not None:
		for i in range(len(zookeeper_hosts)):
			zookeeper_host_ports.append(format(zookeeper_hosts[i] + ":{zookeeper_client_port}"))
	else:
		for i in range(len(zookeeper_hosts)):
			zookeeper_host_ports.append(format(zookeeper_hosts[i] + ":2181"))
	zookeeper_host_port = ",".join(zookeeper_host_ports)
	rest_url = format("http://" + zookeeper_hosts[0] + ":9998")

# Configurations of Spark
# Livy service is depended on Spark thriftserver
spark_thriftserver_hosts = default("/clusterHostInfo/spark_thriftserver_hosts", [])
spark_thriftserver_host = "localhost"
spark_hiveserver2_thrift_port = "10002"
if_spark_exist = False
if len(spark_thriftserver_hosts) == 0:
	app_blacklists.append('spark')
else:
	if_spark_exist = True
	spark_thriftserver_host = spark_thriftserver_hosts[0]
	spark_hiveserver2_thrift_port = str(config['configurations']['spark-hive-site-override']['hive.server2.thrift.port']).strip()
	spark_jobhistoryserver_hosts = default("/clusterHostInfo/spark_jobhistoryserver_hosts", [])
	if len(spark_jobhistoryserver_hosts) > 0:
		spark_history_server_host = spark_jobhistoryserver_hosts[0]
	else:
		spark_history_server_host = "localhost"
	spark_history_ui_port = config['configurations']['spark-defaults']['spark.history.ui.port']
	spark_history_server_url = format("http://{spark_history_server_host}:{spark_history_ui_port}")

# Configurations of Hue metastore database
metastore_database_engines = ['sqlite3','mysql','postgresql_psycopg2','oracle']
metastore_database_engine = config['configurations']['hue-Desktop']['metastore.database.engine'].strip().lower()
metastore_database_host = config['configurations']['hue-Desktop']['metastore.database.host']
metastore_database_port = str(config['configurations']['hue-Desktop']['metastore.database.port']).strip()
metastore_database_name = config['configurations']['hue-Desktop']['metastore.database.name'].strip()
metastore_database_user = config['configurations']['hue-Desktop']['metastore.ConnectionUserName'].strip()
metastore_database_password = str(config['configurations']['hue-Desktop']['metastore.ConnectionPassword']).strip()
metastore_databass_options = config['configurations']['hue-Desktop']['metastore.database.options'].strip()
if metastore_database_engine not in metastore_database_engines or not metastore_database_engine:
	metastore_database_engine = 'sqlite3'

# Configurations of RDBMS
RDBMS_database_engines = ['sqlite','mysql','postgresql','oracle']
RDBMS_database_engine = config['configurations']['hue-RDBMS']['Database.engine'].strip().lower()
RDBMS_nice_name = config['configurations']['hue-RDBMS']['Nice.name'].strip()
RDBMS_database_host = config['configurations']['hue-RDBMS']['Database.host']
RDBMS_database_port = str(config['configurations']['hue-RDBMS']['Database.port']).strip()
RDBMS_database_name = config['configurations']['hue-RDBMS']['Database.name'].strip()
RDBMS_database_user = config['configurations']['hue-RDBMS']['Database.user'].strip()
RDBMS_database_password = str(config['configurations']['hue-RDBMS']['Database.password']).strip()
RDBMS_options = config['configurations']['hue-RDBMS']['options'].strip()
if RDBMS_database_engine not in RDBMS_database_engines or not RDBMS_database_engine:
	RDBMS_database_engine = 'sqlite'
	RDBMS_database_name = '/usr/local/hue/desktop/desktop.db'

user_app_blacklists = config['configurations']['hue-Desktop']['app.blacklist'].split(',')
if len(user_app_blacklists) > 0:
	for user_app_blacklist in user_app_blacklists:
		if user_app_blacklist in hue_apps and user_app_blacklist not in app_blacklists:
			app_blacklists.append(user_app_blacklist)
app_blacklist = ','.join(app_blacklists)

# Ranger hosts
ranger_admin_hosts = default("/clusterHostInfo/ranger_admin_hosts", [])
has_ranger_admin = not len(ranger_admin_hosts) == 0

# Configurations of Hue
hue_install_dir = '/usr/local'
hue_dir = hue_install_dir + '/hue'
hue_conf = hue_dir + '/desktop/conf'
hue_conf_file = format("{hue_conf}/pseudo-distributed.ini")
hue_bin_dir = hue_dir + '/build/env/bin'
hue_tmp_conf= tmp_dir + '/hue_tmp_conf'
hue_user = config['configurations']['hue-env']['hue.user']
hue_group = config['configurations']['hue-env']['hue.group']
hue_log_dir = config['configurations']['hue-env']['hue.log.dir']
hue_pid_dir = config['configurations']['hue-env']['hue.pid.dir']
hue_port = config['configurations']['hue-env']['hue.port']
hue_package_name = config['configurations']['hue-env']['hue.package.name']
hue_version = config['configurations']['hue-env']['hue.version']
hue_log = format("{hue_log_dir}/hue-install.log")
secret_key = config['configurations']['hue-Desktop']['secret.key']

hue_desktop_content = config['configurations']['hue-Desktop']['content']
hue_hadoop_content = config['configurations']['hue-Hadoop']['content']
hue_hive_content = config['configurations']['hue-Hive']['content']
hue_spark_content = config['configurations']['hue-Spark']['content']
hue_oozie_content = config['configurations']['hue-Oozie']['content']
hue_pig_content = config['configurations']['hue-Pig']['content']
hue_hbase_content = config['configurations']['hue-Hbase']['content']
hue_solr_content = config['configurations']['hue-Solr']['content']
hue_zookeeper_content = config['configurations']['hue-Zookeeper']['content']
hue_rdbms_content = config['configurations']['hue-RDBMS']['content']
hue_log_content = config['configurations']['hue-log4j-env']['content']


