#!/bin/bash
#Path to install HUE to e.g. /usr/local/hue
HUE_PATH=$1
# Add Hue user
HUE_USER=$2
echo "Starting Hue install" 
getent passwd $HUE_USER
if [ $? -eq 0 ]; then
	echo "the user exists, no need to create"
else
	echo "creating hue user"
	adduser $HUE_USER
fi
hadoop fs -test -d /user/$HUE_USER
if [ $? -eq 1 ]; then
    echo "Creating user dir in HDFS"
    sudo -u hdfs hdfs dfs -mkdir -p /user/$HUE_USER
    sudo -u hdfs hdfs dfs -chown $HUE_USER /user/hue 
fi
#add the environment variable to /etc/profile
sed -i '$a## ------------SPARK_HOME and HADOOP_CONF_DIR--------------------- ##' /etc/profile
sed -i '$aexport SPARK_HOME=/usr/hdp/current/spark-client' /etc/profile
sed -i '$aexport PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin' /etc/profile
sed -i '$aexport HADOOP_CONF_DIR=/usr/hdp/current/hadoop-client/conf' /etc/profile
source /etc/profile	

