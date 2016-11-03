#### An Ambari Service for Hue
Ambari service for easily installing and managing Hue on HDP cluster.

Authors: 
  - [Kyle Joe](https://github.com/EsharEditor): Hue Install/Config/Start/Stop via Ambari

#### Version
- Hue v3.11.0+
- Ambari v2.4.0+

#### Setup

#### Deploy Hue on existing cluster

- (Optional) To see Hue metrics in Ambari, login to Ambari (admin/admin) and start Ambari Metrics service 
http://$AMBARI_HOST:8080

- To download the Hue service folder, run below
```
VERSION=`hdp-select status hadoop-client | sed 's/hadoop-client - \([0-9]\.[0-9]\).*/\1/'`
rm -rf /var/lib/ambari-server/resources/stacks/HDP/$VERSION/services/HUE  
sudo git clone https://github.com/EsharEditor/ambari-hue-service.git /var/lib/ambari-server/resources/stacks/HDP/$VERSION/services/HUE
```

- Restart Ambari
```
service ambari-server restart
```
- Then you can click on 'Add Service' from the 'Actions' dropdown menu in the bottom left of the Ambari dashboard:

On bottom left -> Actions -> Add service -> check Hue server -> Next -> Next -> Change any config you like (e.g. install dir, port) -> Next -> Deploy

- Also ensure that the install location you are choosing (/usr/local/hue by default) does not exist

- On successful deployment you will see the Hue service as part of Ambari stack and will be able to start/stop the service from here:
![Image](../branch-2.0.0/screenshots/1.png?raw=true)

- You can see the parameters you configured under 'Configs' tab
![Image](../branch-2.0.0/screenshots/2.png?raw=true)
![Image](../branch-2.0.0/screenshots/3.png?raw=true)
![Image](../branch-2.0.0/screenshots/4.png?raw=true)

- One benefit to wrapping the component in Ambari service is that you can now monitor/manage this service remotely via REST API
```
export SERVICE=HUE
export PASSWORD=admin
export AMBARI_HOST=localhost
export CLUSTER=DCenter

#get service status
curl -u admin:$PASSWORD -i -H 'X-Requested-By: ambari' -X GET http://$AMBARI_HOST:8080/api/v1/clusters/$CLUSTER/services/$SERVICE

#start service
curl -u admin:$PASSWORD -i -H 'X-Requested-By: ambari' -X PUT -d '{"RequestInfo": {"context" :"Start $SERVICE via REST"}, "Body": {"ServiceInfo": {"state": "STARTED"}}}' http://$AMBARI_HOST:8080/api/v1/clusters/$CLUSTER/services/$SERVICE

#stop service
curl -u admin:$PASSWORD -i -H 'X-Requested-By: ambari' -X PUT -d '{"RequestInfo": {"context" :"Stop $SERVICE via REST"}, "Body": {"ServiceInfo": {"state": "INSTALLED"}}}' http://$AMBARI_HOST:8080/api/v1/clusters/$CLUSTER/services/$SERVICE
```

#### Configuring Cluster and HUE
Hue uses a configuration file to understand information about Hadoop cluster and where to connect to. We’ll need to configure our Hadoop cluster to accept connections from HUE, and add our cluster information to the HUE configuration file. We’ll need to reconfigure our HDFS, Hive (WebHcatalog), and Oozie services to take advantage of HUE’s features.[tutorials from Hue](http://gethue.com/hadoop-hue-3-on-hdp-installation-tutorial/?replytocom=50032)

  - http://gethue.com/hadoop-hue-3-on-hdp-installation-tutorial/?replytocom=50032

#### Hue Service Action
![Image](../branch-2.0.0/screenshots/5.png?raw=true)
- UserSync: synchronize users from the current system or Ldap server
- DatabaseSync: synchronize metastore from SQLite

#### Use Hue
- The Hue webUI login page should come up at the below link: 
http://$HUE_HOSTNAME:8888
![Image](../branch-2.0.0/screenshots/6.png?raw=true)

#### Remove service

- To remove the Hue service: 
  - Stop the service via Ambari
  - Unregister the service by running below from Ambari node
  
```
export SERVICE=HUE
export PASSWORD=admin
export AMBARI_HOST=localhost

#detect name of cluster
output=`curl -u admin:$PASSWORD -i -H 'X-Requested-By: ambari'  http://$AMBARI_HOST:8080/api/v1/clusters`
CLUSTER=`echo $output | sed -n 's/.*"cluster_name" : "\([^\"]*\)".*/\1/p'`

#unregister service from ambari
curl -u admin:$PASSWORD -i -H 'X-Requested-By: ambari' -X DELETE http://$AMBARI_HOST:8080/api/v1/clusters/$CLUSTER/services/$SERVICE

#if above errors out, run below first to fully stop the service
#curl -u admin:$PASSWORD -i -H 'X-Requested-By: ambari' -X PUT -d '{"RequestInfo": {"context" :"Stop $SERVICE via REST"}, "Body": {"ServiceInfo": {"state": "INSTALLED"}}}' http://$AMBARI_HOST:8080/api/v1/clusters/$CLUSTER/services/$SERVICE
```
- Remove artifacts

```
rm -rf /usr/local/hue*
rm -rf /var/log/hue
rm -rf /var/run/hue
rm /usr/hdp/current/hadoop-client/lib/hue-plugins-3.11.0-SNAPSHOT.jar
```   
