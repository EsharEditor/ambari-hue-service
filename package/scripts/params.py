#!/usr/bin/env python
import os,re
import resource_management.libraries.functions
from resource_management import *
from ambari_commons.os_check import OSCheck
from ambari_commons.str_utils import cbool, cint
from resource_management.libraries.functions import StackFeature
from resource_management.libraries.functions import conf_select
from resource_management.libraries.functions import get_kinit_path
from resource_management.libraries.functions import stack_select
from resource_management.libraries.functions.default import default
from resource_management.libraries.functions.format import format
from resource_management.libraries.functions.get_stack_version import get_stack_version
from resource_management.libraries.functions.stack_features import check_stack_feature
from resource_management.libraries.functions.version import format_stack_version
from resource_management.libraries.resources.hdfs_resource import HdfsResource
from resource_management.libraries.functions.get_not_managed_resources import get_not_managed_resources
from resource_management.libraries.script.script import Script
import status_params
import functools
# a map of the Ambari role to the component name
# for use with <stack-root>/current/<component>
SERVER_ROLE_DIRECTORY_MAP = {
  'HUE_SERVER' : 'hue-server',
}

component_directory = Script.get_component_from_role(SERVER_ROLE_DIRECTORY_MAP, "HUE_SERVER")
config = Script.get_config()
tmp_dir = Script.get_tmp_dir()
stack_root = Script.get_stack_root()
# Hue download url
download_url = 'cat /etc/yum.repos.d/HDP.repo | grep "baseurl" | awk -F \'=\' \'{print $2"hue/hue-3.11.0.tgz"}\''
# New Cluster Stack Version that is defined during the RESTART of a Rolling Upgrade
version = default("/commandParams/version", None)
stack_name = default("/hostLevelParams/stack_name", None)
#e.g. /var/lib/ambari-agent/cache/stacks/HDP/$VERSION/services/HUE/package
service_packagedir = os.path.realpath(__file__).split('/scripts')[0]
cluster_name = str(config['clusterName'])
ambari_server_hostname = config['clusterHostInfo']['ambari_server_host'][0]

#hue_apps = ['security','pig','filebrowser','jobbrowser','zookeeper','search','rdbms','metastore','spark','beeswax','jobsub','hbase','oozie','indexer']
hue_hdfs_module_enabled = config['configurations']['hue-env']['hue-hdfs-module-enabled']
hue_yarn_module_enabled = config['configurations']['hue-env']['hue-yarn-module-enabled']
hue_hive_module_enabled = config['configurations']['hue-env']['hue-hive-module-enabled']
hue_hbase_module_enabled = config['configurations']['hue-env']['hue-hbase-module-enabled']
hue_zookeeper_module_enabled = config['configurations']['hue-env']['hue-zookeeper-module-enabled']
hue_oozie_module_enabled = config['configurations']['hue-env']['hue-oozie-module-enabled']
hue_notebook_module_enabled = config['configurations']['hue-env']['hue-notebook-module-enabled']
hue_rdbms_module_enabled = config['configurations']['hue-env']['hue-rdbms-module-enabled']
hue_solr_module_enabled = config['configurations']['hue-env']['hue-solr-module-enabled']
hue_pig_module_enabled = config['configurations']['hue-env']['hue-pig-module-enabled']
hue_impala_module_enabled = config['configurations']['hue-env']['hue-impala-module-enabled']
hue_spark_module_enabled = config['configurations']['hue-env']['hue-spark-module-enabled']
# Comma separated list of apps to not load at server startup.
app_blacklists = ['security','sqoop']
notebook_show_notebooks = True
if hue_hdfs_module_enabled == 'No':
  app_blacklists.append('filebrowser')
if hue_yarn_module_enabled == 'No':
  app_blacklists.append('jobbrowser')
if hue_hive_module_enabled == 'No':
  app_blacklists.append('beeswax')
  app_blacklists.append('metastore')
if hue_hbase_module_enabled == 'No':
  app_blacklists.append('hbase')
if hue_zookeeper_module_enabled == 'No':
  app_blacklists.append('zookeeper')
if hue_oozie_module_enabled == 'No':
  app_blacklists.append('oozie')
  app_blacklists.append('pig')
  app_blacklists.append('jobsub')
if hue_notebook_module_enabled == 'No':
  notebook_show_notebooks = False
if hue_rdbms_module_enabled == 'No':
  app_blacklists.append('rdbms')
if hue_solr_module_enabled == 'No':
  app_blacklists.append('search')
if hue_pig_module_enabled == 'No':
  app_blacklists.append('pig')
if hue_impala_module_enabled == 'No':
  app_blacklists.append('impala')
if hue_spark_module_enabled == 'No':
  app_blacklists.append('spark')
app_blacklists = list(set(app_blacklists))
app_blacklist = ','.join(app_blacklists)

java_home = config['hostLevelParams']['java_home']
http_host = config['hostname']
http_port = config['configurations']['hue-env']['http_port']
hue_pid_dir = config['configurations']['hue-env']['hue_pid_dir']
hue_log_dir = config['configurations']['hue-env']['hue_log_dir']
hue_server_pid_file = os.path.join(hue_pid_dir, 'hue-server.pid')
hue_log_file = os.path.join(hue_log_dir, 'hue-install.log')
hue_user = config['configurations']['hue-env']['hue_user']
hue_group = config['configurations']['hue-env']['hue_group']
hue_local_home_dir = os.path.expanduser("~{0}".format(hue_user))
hue_hdfs_home_dir = format('/user/{hue_user}')
hue_install_dir = '/usr/local'
hue_dir = format('{hue_install_dir}/hue')
hue_conf_dir = format('{hue_dir}/desktop/conf')
hue_bin_dir = format('{hue_dir}/build/env/bin')
# configurations of metastore 
metastore_db_flavor =  (config['configurations']['hue-desktop-site']['DB_FLAVOR']).lower()
metastore_db_host = config['configurations']['hue-desktop-site']['db_host'].strip()
metastore_db_port = str(config['configurations']['hue-desktop-site']['db_port']).strip()
metastore_db_name = config['configurations']['hue-desktop-site']['db_name'].strip()
metastore_db_user = config['configurations']['hue-desktop-site']['db_user'].strip()
metastore_db_password = str(config['configurations']['hue-desktop-site']['db_password']).strip()
metastore_db_password_script = config['configurations']['hue-desktop-site']['db_password_script']
metastore_db_options = config['configurations']['hue-desktop-site']['db_options'].strip()
# configurations of usersync
usersync_enabled = config['configurations']['hue-ugsync-site']['usersync.enabled']
usersync_source = (config['configurations']['hue-ugsync-site']['SYNC_SOURCE']).lower()
usersync_unix_minUserId = config['configurations']['hue-ugsync-site']['usersync.unix.minUserId'].strip()
usersync_unix_maxUserId = config['configurations']['hue-ugsync-site']['usersync.unix.maxUserId'].strip()
usersync_unix_minGroupId = config['configurations']['hue-ugsync-site']['usersync.unix.minGroupId'].strip()
usersync_unix_maxGroupId = config['configurations']['hue-ugsync-site']['usersync.unix.maxGroupId'].strip()
usersync_unix_group_file = config['configurations']['hue-ugsync-site']['usersync.unix.group.file']
usersync_unix_password_file = config['configurations']['hue-ugsync-site']['usersync.unix.password.file']
usersync_sleeptimeinmillisbetweensynccycle = config['configurations']['hue-ugsync-site']['usersync.sleeptimeinmillisbetweensynccycle']
usersync_ldap_base_dn = config['configurations']['hue-ugsync-site']['usersync.ldap.base.dn']
usersync_ldap_url = config['configurations']['hue-ugsync-site']['usersync.ldap.url']
usersync_ldap_nt_domain = config['configurations']['hue-ugsync-site']['usersync.ldap.nt.domain']
usersync_ldap_cert = config['configurations']['hue-ugsync-site']['usersync.ldap.cert']
usersync_ldap_use_start_tls = config['configurations']['hue-ugsync-site']['usersync.ldap.use.start.tls']
usersync_ldap_bind_dn = config['configurations']['hue-ugsync-site']['usersync.ldap.bind.dn']
usersync_ldap_bind_password = config['configurations']['hue-ugsync-site']['usersync.ldap.bind.password']
usersync_ldap_bind_password_script = config['configurations']['hue-ugsync-site']['usersync.ldap.bind.password.script']
usersync_ldap_username_pattern = config['configurations']['hue-ugsync-site']['usersync.ldap.username.pattern']
usersync_ldap_create_users_on_login = config['configurations']['hue-ugsync-site']['usersync.ldap.create.users.on.login']
usersync_ldap_sync_groups_on_login = config['configurations']['hue-ugsync-site']['usersync.ldap.sync.groups.on.login']
usersync_ldap_ignore_username_case = config['configurations']['hue-ugsync-site']['usersync.ldap.ignore.username.case']
usersync_ldap_force_username_lowercase = config['configurations']['hue-ugsync-site']['usersync.ldap.force.username.lowercase']
usersync_ldap_force_username_uppercase = config['configurations']['hue-ugsync-site']['usersync.ldap.force.username.uppercase']
usersync_ldap_search_bind_authentication = config['configurations']['hue-ugsync-site']['usersync.ldap.search.bind.authentication']
usersync_ldap_subgroups = config['configurations']['hue-ugsync-site']['usersync.ldap.subgroups']
usersync_ldap_nested_members_search_depth = config['configurations']['hue-ugsync-site']['usersync.ldap.nested.members.search.depth']
usersync_ldap_follow_referrals = config['configurations']['hue-ugsync-site']['usersync.ldap.follow.referrals']
usersync_ldap_debug = config['configurations']['hue-ugsync-site']['usersync.ldap.debug']
usersync_ldap_debug_level = config['configurations']['hue-ugsync-site']['usersync.ldap.debug.level']
usersync_ldap_trace_level = config['configurations']['hue-ugsync-site']['usersync.ldap.trace.level']
usersync_ldap_user_searchfilter = config['configurations']['hue-ugsync-site']['usersync.ldap.user.searchfilter']
usersync_ldap_user_name_attribute = config['configurations']['hue-ugsync-site']['usersync.ldap.user.name.attribute']
usersync_ldap_group_searchenabled = config['configurations']['hue-ugsync-site']['usersync.ldap.group.searchenabled']
usersync_ldap_group_searchfilter = config['configurations']['hue-ugsync-site']['usersync.ldap.group.searchfilter']
usersync_ldap_group_name_attribute = config['configurations']['hue-ugsync-site']['usersync.ldap.group.name.attribute']
usersync_ldap_group_member_attribute = config['configurations']['hue-ugsync-site']['usersync.ldap.group.member.attribute']

# configurations of security
security_enabled = config['configurations']['cluster-env']['security_enabled']
if security_enabled:
  HTTP_principal = config['configurations']['hdfs-site']['dfs.web.authentication.kerberos.principal']
  HTTP_keytab = config['configurations']['hdfs-site']['dfs.web.authentication.kerberos.keytab']
  hue_principal = config['configurations']['hue-desktop-site']['kerberos_hue_principal'].replace('_HOST',http_host)
  hue_keytab = config['configurations']['hue-desktop-site']['kerberos_hue_keytab']
  kinit_path = config['configurations']['hue-desktop-site']['kerberos_kinit_path']
  zk_principal = config['configurations']['zookeeper-env']['zookeeper_principal_name'].replace('_HOST',http_host)
  zk_keytab = config['configurations']['zookeeper-env']['zookeeper_principal_name']

# configurations of HDFS
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
  namenode_address = format('hdfs://{dfs_ha_nameservices}')
  logical_name = dfs_ha_nameservices
  hdfs_httpfs_host = config['configurations']['hue-hadoop-site']['hdfs_httpfs_host']
  # if kerberos is disabled, using HttpFS . Otherwise using WebHDFS.
  if hdfs_httpfs_host in namenode_host and not security_enabled:
    webhdfs_url = format('http://' + hdfs_httpfs_host + ':14000/webhdfs/v1')
  else:
    webhdfs_url = format('http://' + hdfs_httpfs_host + ':50070/webhdfs/v1')
else:
  dfs_namenode_http_address = config['configurations']['hdfs-site']['dfs.namenode.http-address']
  webhdfs_url = format('http://' + dfs_namenode_http_address + '/webhdfs/v1')
hadoop_ssl_cert_ca_verify = config['configurations']['hue-hadoop-site']['ssl_cert_ca_verify']
hadoop_conf_dir = config['configurations']['hue-hadoop-site']['hadoop_conf_dir']
# [filebrowser]
filebrowser_archive_upload_tempdir = config['configurations']['hue-hadoop-site']['filebrowser_archive_upload_tempdir']
filebrowser_show_download_button = config['configurations']['hue-hadoop-site']['filebrowser_show_download_button']
filebrowser_show_upload_button = config['configurations']['hue-hadoop-site']['filebrowser_show_upload_button']
# [jobbrowser]
jobbrowser_share_jobs = config['configurations']['hue-hadoop-site']['jobbrowser_share_jobs']
jobbrowser_disable_killing_jobs = config['configurations']['hue-hadoop-site']['jobbrowser_disable_killing_jobs']
jobbrowser_log_offset = config['configurations']['hue-hadoop-site']['jobbrowser_log_offset']
# [jobsub]
jobsub_local_data_dir = config['configurations']['hue-hadoop-site']['jobsub_sample_data_dir']
jobsub_sample_data_dir = config['configurations']['hue-hadoop-site']['jobsub_sample_data_dir']

hdfs_user = config['configurations']['hadoop-env']['hdfs_user']
hadoop_bin_dir = stack_select.get_hadoop_dir('bin')
hadoop_conf_dir = conf_select.get_hadoop_conf_dir()
hdfs_site = config['configurations']['hdfs-site']
default_fs = config['configurations']['core-site']['fs.defaultFS']
dfs_type = default("/commandParams/dfs_type", "")
hdfs_user_keytab = config['configurations']['hadoop-env']['hdfs_user_keytab']
hdfs_principal_name = config['configurations']['hadoop-env']['hdfs_principal_name']
kinit_path_local = get_kinit_path(default('/configurations/kerberos-env/executable_search_paths', None))
# create partial functions with common arguments for every HdfsResource call
# to create hdfs directory we need to call params.HdfsResource in code
HdfsResource = functools.partial(
    HdfsResource,
    user=hdfs_user,
    hdfs_resource_ignore_file='/var/lib/ambari-agent/data/.hdfs_resource_ignore',
    security_enabled=security_enabled,
    keytab=hdfs_user_keytab,
    kinit_path_local=kinit_path_local,
    hadoop_bin_dir=hadoop_bin_dir,
    hadoop_conf_dir=hadoop_conf_dir,
    principal_name=hdfs_principal_name,
    hdfs_site=hdfs_site,
    default_fs=default_fs,
    immutable_paths=get_not_managed_resources(),
    dfs_type=dfs_type
)

# configurations of Yarn
resourcemanager_hosts = default("/clusterHostInfo/rm_host", [])
resourcemanager_host = str(resourcemanager_hosts)
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

# configurations of Oozie
# Pig and Jobsub service are depended on oozie in Hue
oozie_servers_hosts = default("/clusterHostInfo/oozie_server", [])
oozie_url='http://localhost:11000/oozie'
if len(oozie_servers_hosts) > 0:
  oozie_url = config['configurations']['oozie-site']['oozie.base.url']
oozie_local_data_dir = config['configurations']['hue-oozie-site']['local_data_dir']
oozie_sample_data_dir = config['configurations']['hue-oozie-site']['sample_data_dir']
oozie_remote_data_dir = config['configurations']['hue-oozie-site']['remote_data_dir']
oozie_jobs_count = config['configurations']['hue-oozie-site']['oozie_jobs_count']
oozie_enable_cron_scheduling = config['configurations']['hue-oozie-site']['enable_cron_scheduling']
oozie_enable_document_action = config['configurations']['hue-oozie-site']['enable_document_action']
oozie_remote_deployement_dir = config['configurations']['hue-oozie-site']['remote_deployement_dir']

# configurations of Pig
pig_local_sample_dir = config['configurations']['hue-pig-site']['local_sample_dir']
pig_remote_data_dir = config['configurations']['hue-pig-site']['remote_data_dir']

# configurations of Solr
solr_master_hosts = default("/clusterHostInfo/solr_master_hosts", [])
solr_master_hosts.sort()
solr_url='http://localhost:8983/solr/'
if len(solr_master_hosts) > 0:
  solr_port = config['configurations']['solr-env']['solr.port']
  solr_znode = config['configurations']['solr-config']['solr.znode']
  solr_master_host = solr_master_hosts[0]
  solr_url = format('http://' + solr_master_host + ':' + str(solr_port) + solr_znode + '/')
solr_empty_query = config['configurations']['hue-solr-site']['empty_query']
solr_latest = config['configurations']['hue-solr-site']['latest']
solr_ssl_cert_ca_verify = config['configurations']['hue-solr-site']['ssl_cert_ca_verify']
solr_zk_path = config['configurations']['hue-solr-site']['solr_zk_path']
solr_enable_new_indexer = config['configurations']['hue-solr-site']['enable_new_indexer']
solr_solrctl_path = config['configurations']['hue-solr-site']['solrctl_path']

# configurations of Hive and Pig
# Hive service is depended on Pig in ambari
hive_server_hosts =  default("/clusterHostInfo/hive_server_host", [])
if len(hive_server_hosts) > 0:
  hive_server_host = config['clusterHostInfo']['hive_server_host'][0]
  hive_transport_mode = config['configurations']['hive-site']['hive.server2.transport.mode']
  if hive_transport_mode.lower() == "http":
    hive_server_port = config['configurations']['hive-site']['hive.server2.thrift.http.port']
  else:
    hive_server_port = default('/configurations/hive-site/hive.server2.thrift.port',"10000")
hive_conf_dir = config['configurations']['hue-hive-site']['hive_conf_dir']
hive_server_conn_timeout = config['configurations']['hue-hive-site']['server_conn_timeout']
hive_use_get_log_api = config['configurations']['hue-hive-site']['use_get_log_api']
hive_list_partitions_limit = config['configurations']['hue-hive-site']['list_partitions_limit']
hive_query_partitions_limit = config['configurations']['hue-hive-site']['query_partitions_limit']
hive_download_cell_limit = config['configurations']['hue-hive-site']['download_cell_limit']
hive_close_queries = config['configurations']['hue-hive-site']['close_queries']
hive_thrift_version = config['configurations']['hue-hive-site']['thrift_version']
hive_config_whitelist = config['configurations']['hue-hive-site']['config_whitelist']
hive_auth_username = config['configurations']['hue-hive-site']['auth_username']
hive_auth_password = config['configurations']['hue-hive-site']['auth_password']
hive_ssl_cacerts = config['configurations']['hue-hive-site']['ssl_cacerts']
hive_ssl_validate = config['configurations']['hue-hive-site']['ssl_validate']

# configurations of Hbase
hbase_master_hosts = default("/clusterHostInfo/hbase_master_hosts", [])
hbase_clusters = []
hbase_cluster = ''
if len(hbase_master_hosts) > 0:
  for i in range(len(hbase_master_hosts)):
    hbase_clusters.append(format("(Cluster" + str(i+1) + "|" + hbase_master_hosts[i] + ":9090)"))
  hbase_cluster = ",".join(hbase_clusters)
else:
  hbase_cluster='(Cluster|localhost:9090)'
hbase_conf_dir = config['configurations']['hue-hbase-site']['hbase_conf_dir']
hbase_truncate_limit = config['configurations']['hue-hbase-site']['truncate_limit']
hbase_thrift_transport = config['configurations']['hue-hbase-site']['thrift_transport']

# configurations of Zookeeper
zookeeper_hosts = default("/clusterHostInfo/zookeeper_hosts", [])
zookeeper_hosts.sort()
zookeeper_client_port = default('/configurations/zoo.cfg/clientPort', None)
zookeeper_host_ports = []
zookeeper_host_port = ''
zookeeper_rest_url = ''
if len(zookeeper_hosts) > 0:
  if zookeeper_client_port is not None:
    for i in range(len(zookeeper_hosts)):
  	  zookeeper_host_ports.append(format(zookeeper_hosts[i] + ":{zookeeper_client_port}"))
  else:
    for i in range(len(zookeeper_hosts)):
  	  zookeeper_host_ports.append(format(zookeeper_hosts[i] + ":2181"))
  zookeeper_host_port = ",".join(zookeeper_host_ports)
  zookeeper_rest_url = format("http://" + zookeeper_hosts[0] + ":9998")

# configurations of Spark
spark_thriftserver_hosts = default("/clusterHostInfo/spark_thriftserver_hosts", [])
spark_thriftserver_host = "localhost"
spark_hiveserver2_thrift_port = "10002"
spark_history_server_url = ''
if len(spark_thriftserver_hosts) > 0:
  spark_thriftserver_host = spark_thriftserver_hosts[0]
  spark_hiveserver2_thrift_port = str(config['configurations']['spark-hive-site-override']['hive.server2.thrift.port']).strip()
  spark_jobhistoryserver_hosts = default("/clusterHostInfo/spark_jobhistoryserver_hosts", [])
  if len(spark_jobhistoryserver_hosts) > 0:
    spark_history_server_host = spark_jobhistoryserver_hosts[0]
  else:
    spark_history_server_host = "localhost"
  spark_history_ui_port = config['configurations']['spark-defaults']['spark.history.ui.port']
  spark_history_server_url = format("http://{spark_history_server_host}:{spark_history_ui_port}")
livy_server_hosts = default("/clusterHostInfo/livy_server_hosts", [])
livy_server_host = 'localhost'
livy_server_port = '8983'
if len(livy_server_hosts) > 0:
  livy_server_host = livy_server_hosts[0]
  livy_server_port = config['configurations']['livy-conf']['livy.server.port']
livy_server_session_kind = config['configurations']['hue-spark-site']['livy_server_session_kind']

# configurations of RDBMS
rdbms_sqlite_engine = config['configurations']['hue-rdbms-site']['sqlite_engine']
rdbms_sqlite_nice_name = config['configurations']['hue-rdbms-site']['sqlite_nice_name']
rdbms_sqlite_name = config['configurations']['hue-rdbms-site']['sqlite_name'].strip()
rdbms_sqlite_options = config['configurations']['hue-rdbms-site']['sqlite_options']
rdbms_mysql_engine = config['configurations']['hue-rdbms-site']['mysql_engine']
rdbms_mysql_nice_name = config['configurations']['hue-rdbms-site']['mysql_nice_name']
rdbms_mysql_name = config['configurations']['hue-rdbms-site']['mysql_name'].strip()
rdbms_mysql_host = config['configurations']['hue-rdbms-site']['mysql_host']
rdbms_mysql_port = str(config['configurations']['hue-rdbms-site']['mysql_port']).strip()
rdbms_mysql_user = config['configurations']['hue-rdbms-site']['mysql_user']
rdbms_mysql_password = str(config['configurations']['hue-rdbms-site']['mysql_password']).strip()
rdbms_mysql_options = config['configurations']['hue-rdbms-site']['mysql_options']
rdbms_postgresql_engine = config['configurations']['hue-rdbms-site']['postgresql_engine']
rdbms_postgresql_nice_name = config['configurations']['hue-rdbms-site']['postgresql_nice_name']
rdbms_postgresql_name = config['configurations']['hue-rdbms-site']['postgresql_name'].strip()
rdbms_postgresql_host = config['configurations']['hue-rdbms-site']['postgresql_host']
rdbms_postgresql_port = str(config['configurations']['hue-rdbms-site']['postgresql_port']).strip()
rdbms_postgresql_user = config['configurations']['hue-rdbms-site']['postgresql_user'].strip()
rdbms_postgresql_password = str(config['configurations']['hue-rdbms-site']['postgresql_password']).strip()
rdbms_postgresql_options = config['configurations']['hue-rdbms-site']['postgresql_options']
rdbms_oracle_engine = config['configurations']['hue-rdbms-site']['oracle_engine']
rdbms_oracle_nice_name = config['configurations']['hue-rdbms-site']['oracle_nice_name']
rdbms_oracle_name = config['configurations']['hue-rdbms-site']['oracle_name'].strip()
rdbms_oracle_host = config['configurations']['hue-rdbms-site']['oracle_host']
rdbms_oracle_port = str(config['configurations']['hue-rdbms-site']['oracle_port']).strip()
rdbms_oracle_user = config['configurations']['hue-rdbms-site']['oracle_user'].strip()
rdbms_oracle_password = str(config['configurations']['hue-rdbms-site']['oracle_password']).strip()
rdbms_oracle_options = config['configurations']['hue-rdbms-site']['oracle_options']

# configurations of Notebook
notebook_enable_batch_execute = config['configurations']['hue-notebook-site']['enable_batch_execute']
notebook_enable_query_builder = config['configurations']['hue-notebook-site']['enable_query_builder']
notebook_enable_query_scheduling = config['configurations']['hue-notebook-site']['enable_query_scheduling']
notebook_github_remote_url = config['configurations']['hue-notebook-site']['github_remote_url']
notebook_github_api_url = config['configurations']['hue-notebook-site']['github_api_url']
notebook_github_client_id = config['configurations']['hue-notebook-site']['github_client_id']
notebook_github_client_secret = config['configurations']['hue-notebook-site']['github_client_secret']
notebook_enable_dbproxy_server = config['configurations']['hue-notebook-site']['enable_dbproxy_server']

# Ranger hosts
ranger_admin_hosts = default("/clusterHostInfo/ranger_admin_hosts", [])
has_ranger_admin = not len(ranger_admin_hosts) == 0

# configurations of Desktop
desktop_secret_key = config['configurations']['hue-desktop-site']['secret_key']
desktop_secret_key_script = config['configurations']['hue-desktop-site']['secret_key_script']
desktop_time_zone = config['configurations']['hue-desktop-site']['time_zone']
desktop_django_debug_mode = config['configurations']['hue-desktop-site']['django_debug_mode']
desktop_database_logging = config['configurations']['hue-desktop-site']['database_logging']
desktop_send_dbug_messages = config['configurations']['hue-desktop-site']['send_dbug_messages']
desktop_http_500_debug_mode = config['configurations']['hue-desktop-site']['http_500_debug_mode']
desktop_memory_profiler = config['configurations']['hue-desktop-site']['memory_profiler']
desktop_django_server_email = config['configurations']['hue-desktop-site']['django_server_email']
desktop_django_email_backend = config['configurations']['hue-desktop-site']['django_email_backend']
desktop_server_user = hue_user
desktop_server_group = hue_group
desktop_default_user = config['configurations']['hue-desktop-site']['default_user']
desktop_default_hdfs_superuser = config['configurations']['hue-desktop-site']['default_hdfs_superuser']
desktop_enable_server = config['configurations']['hue-desktop-site']['enable_server']
desktop_cherrypy_server_threads = config['configurations']['hue-desktop-site']['cherrypy_server_threads']
desktop_ssl_enable = config['configurations']['hue-desktop-site']['ssl_enable']
desktop_ssl_certificate = config['configurations']['hue-desktop-site']['ssl_certificate']
desktop_ssl_private_key = config['configurations']['hue-desktop-site']['ssl_private_key']
desktop_ssl_certificate_chain = config['configurations']['hue-desktop-site']['ssl_certificate_chain']
desktop_ssl_password = config['configurations']['hue-desktop-site']['ssl_password']
desktop_ssl_password_script = config['configurations']['hue-desktop-site']['ssl_password_script']
desktop_secure_content_type_nosniff = config['configurations']['hue-desktop-site']['secure_content_type_nosniff']
desktop_secure_browser_xss_filter = config['configurations']['hue-desktop-site']['secure_browser_xss_filter']
desktop_secure_content_security_policy = config['configurations']['hue-desktop-site']['secure_content_security_policy']
desktop_secure_ssl_redirect = config['configurations']['hue-desktop-site']['secure_ssl_redirect']
desktop_secure_redirect_host = config['configurations']['hue-desktop-site']['secure_redirect_host']
desktop_secure_redirect_exempt = config['configurations']['hue-desktop-site']['secure_redirect_exempt']
desktop_secure_hsts_seconds = config['configurations']['hue-desktop-site']['secure_hsts_seconds']
desktop_secure_hsts_include_subdomains = config['configurations']['hue-desktop-site']['secure_hsts_include_subdomains']
desktop_ssl_cipher_list = config['configurations']['hue-desktop-site']['ssl_cipher_list']
desktop_ssl_cacerts = config['configurations']['hue-desktop-site']['ssl_cacerts']
desktop_validate = config['configurations']['hue-desktop-site']['validate']
desktop_auth_username = config['configurations']['hue-desktop-site']['auth_username']
desktop_auth_password = config['configurations']['hue-desktop-site']['auth_password']
desktop_default_site_encoding = config['configurations']['hue-desktop-site']['default_site_encoding']
desktop_collect_usage = config['configurations']['hue-desktop-site']['collect_usage']
desktop_leaflet_tile_layer = config['configurations']['hue-desktop-site']['leaflet_tile_layer']
desktop_leaflet_tile_layer_attribution = config['configurations']['hue-desktop-site']['leaflet_tile_layer_attribution']
desktop_http_x_frame_options = config['configurations']['hue-desktop-site']['http_x_frame_options']
desktop_use_x_forwarded_host = config['configurations']['hue-desktop-site']['use_x_forwarded_host']
desktop_secure_proxy_ssl_header = config['configurations']['hue-desktop-site']['secure_proxy_ssl_header']
desktop_middleware = config['configurations']['hue-desktop-site']['middleware']
desktop_redirect_whitelist = config['configurations']['hue-desktop-site']['redirect_whitelist']
desktop_use_new_editor = config['configurations']['hue-desktop-site']['use_new_editor']
desktop_editor_autocomplete_timeout = config['configurations']['hue-desktop-site']['editor_autocomplete_timeout']
desktop_use_default_configuration = config['configurations']['hue-desktop-site']['use_default_configuration']
desktop_audit_event_log_dir = config['configurations']['hue-desktop-site']['audit_event_log_dir']
desktop_audit_log_max_file_size = config['configurations']['hue-desktop-site']['audit_log_max_file_size']
desktop_log_redaction_file = config['configurations']['hue-desktop-site']['log_redaction_file']
desktop_allowed_hosts = config['configurations']['hue-desktop-site']['allowed_hosts']
desktop_session_ttl = config['configurations']['hue-desktop-site']['session_ttl']
desktop_session_secure = config['configurations']['hue-desktop-site']['session_secure']
desktop_session_http_only = config['configurations']['hue-desktop-site']['session_http_only']
desktop_session_expire_at_browser_close = config['configurations']['hue-desktop-site']['session_expire_at_browser_close']
desktop_smtp_host = config['configurations']['hue-desktop-site']['smtp_host']
desktop_smtp_port = config['configurations']['hue-desktop-site']['smtp_port']
desktop_smtp_user = config['configurations']['hue-desktop-site']['smtp_user']
desktop_smtp_password = config['configurations']['hue-desktop-site']['smtp_password']
desktop_smtp_tls = config['configurations']['hue-desktop-site']['smtp_tls']
desktop_smtp_default_from_email = config['configurations']['hue-desktop-site']['smtp_default_from_email']
desktop_oauth_consumer_key = config['configurations']['hue-desktop-site']['oauth_consumer_key']
desktop_oauth_consumer_secret = config['configurations']['hue-desktop-site']['oauth_consumer_secret']
desktop_oauth_request_token_url = config['configurations']['hue-desktop-site']['oauth_request_token_url']
desktop_oauth_access_token_url = config['configurations']['hue-desktop-site']['oauth_access_token_url']
desktop_oauth_authenticate_url = config['configurations']['hue-desktop-site']['oauth_authenticate_url']
desktop_metrics_enable_web_metrics = config['configurations']['hue-desktop-site']['metrics_enable_web_metrics']
desktop_metrics_location = config['configurations']['hue-desktop-site']['metrics_location']
desktop_metrics_collection_interval = config['configurations']['hue-desktop-site']['metrics_collection_interval']

desktop_auth_backend = config['configurations']['hue-auth-site']['backend']
desktop_auth_user_aug = config['configurations']['hue-auth-site']['user_aug']
desktop_auth_pam_service = config['configurations']['hue-auth-site']['pam_service']
desktop_auth_remote_user_header = config['configurations']['hue-auth-site']['remote_user_header']
desktop_auth_ignore_username_case = config['configurations']['hue-auth-site']['ignore_username_case']
desktop_auth_force_username_lowercase = config['configurations']['hue-auth-site']['force_username_lowercase']
desktop_auth_force_username_uppercase = config['configurations']['hue-auth-site']['force_username_uppercase']
desktop_auth_expires_after = config['configurations']['hue-auth-site']['expires_after']
desktop_auth_expire_superusers = config['configurations']['hue-auth-site']['expire_superusers']
desktop_auth_idle_session_timeout = config['configurations']['hue-auth-site']['idle_session_timeout']
desktop_auth_change_default_password = config['configurations']['hue-auth-site']['change_default_password']
desktop_auth_login_failure_limit = config['configurations']['hue-auth-site']['login_failure_limit']
desktop_auth_login_lock_out_at_failure = config['configurations']['hue-auth-site']['login_lock_out_at_failure']
desktop_auth_login_cooloff_time = config['configurations']['hue-auth-site']['login_cooloff_time']
desktop_auth_login_lock_out_use_user_agent = config['configurations']['hue-auth-site']['login_lock_out_use_user_agent']
desktop_auth_login_lock_out_by_combination_user_and_ip = config['configurations']['hue-auth-site']['login_lock_out_by_combination_user_and_ip']
desktop_auth_behind_reverse_proxy = config['configurations']['hue-auth-site']['behind_reverse_proxy']
desktop_auth_reverse_proxy_header = config['configurations']['hue-auth-site']['reverse_proxy_header']

hue_log_content = config['configurations']['hue-log4j-env']['content']
hue_pseudodistributed_content = config['configurations']['pseudo-distributed.ini']['content']



