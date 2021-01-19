#!/usr/bin/env python3

import os
import pwd
import types
import click

# We can't use AvroProducer since it doesn't support string keys, see: https://github.com/confluentinc/confluent-kafka-python/issues/428
from confluent_kafka import avro, Producer
from confluent_kafka.avro import CachedSchemaRegistryClient
from confluent_kafka.avro.serializer.message_serializer import MessageSerializer as AvroSerde
from avro.schema import Field

value_schema_str = """
{
   "namespace" : "org.jlab.kafka.alarms",
   "name"      : "RegisteredAlarm",
   "type"      : "record",
   "fields"    : [
     {
       "name" : "producer",
       "type" : [
         {
           "name"   : "DirectCAAlarm",
           "type"   : "record",
           "fields" : [
             {
               "name" : "pv",
               "type" : "string",
               "doc"  : "The name of the EPICS CA PV, which can be correlated with the key of the epics-channels topic"
             }
           ]
         },
         {
           "name"   : "StreamRuleAlarm",
           "type"   : "record",
           "fields" : [
             {
               "name" : "jar",
               "type" : "string",
               "doc"  : "Name of the Java jar file containing the stream rule logic, stored in the stream rule engine rules directory"
             }
           ]
         }
       ],
       "doc"  : "Indicates how this alarm is produced, useful for producers to monitor when new alarms are added/removed"
     },
     {
       "name" : "location",
       "type" : {
           "name"    : "AlarmLocation",
           "type"    : "enum",
           "symbols" : ["INJ","NL","SL","HA","HB","HC","HD"],
           "doc"     : "The alarm location" 
       }
     },
     {
       "name" : "category",
       "type" : {
           "name"    : "AlarmCategory",
           "type"    : "enum",
           "symbols" : ["Magnet","Vacuum","RF","RADCON","Safety"],
           "doc"     : "The alarm category, useful for consumers to filter out alarms of interest"
       }
     },
     {
        "name"    : "maxshelveduration",
        "type"    : ["null", "int"],
        "doc"     : "Maximum amount of time an alarm is allowed to be shelved in seconds; zero means alarm cannot be shelved and null means no limit",
        "default" : null
     },
     {
        "name"    : "latching",
        "type"    : "boolean",
        "default" : false,
        "doc"     : "Indicates whether this alarm latches when activated and can only be cleared after an explicit acknowledgement"
     },
     {
       "name" : "docurl",
       "type" : "string",
       "doc"  : "The relative URL to documentation for this alarm from base path https://alarms.jlab.org/docs"
     },
     {
       "name" : "edmpath",
       "type" : "string",
       "doc"  : "Relative path to ops fiefdom EDM screen most useful for this alarm from base path /cs/mccops/edm"
     }
  ]
}
"""

value_schema = avro.loads(value_schema_str)

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered')

bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9092')

conf = {'url': os.environ.get('SCHEMA_REGISTRY', 'http://localhost:8081')}
schema_registry = CachedSchemaRegistryClient(conf)

avro_serde = AvroSerde(schema_registry)
serialize_avro = avro_serde.encode_record_with_schema

p = Producer({
    'bootstrap.servers': bootstrap_servers,
    'on_delivery': delivery_report})

topic = 'registered-alarms'

hdrs = [('user', pwd.getpwuid(os.getuid()).pw_name),('producer','set-registered.py'),('host',os.uname().nodename)]

def send() :
    if params.value is None:
        val_payload = None
    else:
        val_payload = serialize_avro(topic, value_schema, params.value, is_key=False)

    p.produce(topic=topic, value=val_payload, key=params.key, headers=hdrs)
    p.flush()

@click.command()
@click.option('--unset', is_flag=True, help="Remove the alarm")
@click.option('--producerpv', help="The name of the EPICS CA PV that directly powers this alarm, only needed if not using producerJar")
@click.option('--producerjar', help="The name of the Java JAR file containing the stream rules powering this alarm, only needed if not using producerPv")
@click.option('--location', type=click.Choice(['INJ', 'NL', 'SL', 'HA', 'HB', 'HC', 'HD']), help="The alarm location")
@click.option('--category', type=click.Choice(['Magnet', 'Vacuum', 'RF', 'RADCON', 'Safety']), help="The alarm category")
@click.option('--maxshelveduration', type=click.INT, help="Maximum amount of time an alarm is allowed to be shelved in seconds; zero means alarm cannot be shelved and null means no limit")
@click.option('--latching', is_flag=True, help="Indicate that the alarm latches and requires acknowledgement to clear")
@click.option('--docurl', help="Relative path to documentation from https://alarms.jlab.org/doc")
@click.option('--edmpath', help="Relative path to OPS fiefdom EDM screen from /cs/mccops/edm")
@click.argument('name')

def cli(unset, producerpv, producerjar, location, category, maxshelveduration, latching, docurl, edmpath, name):
    global params

    params = types.SimpleNamespace()

    params.key = name

    if unset:
        params.value = None
    else:
        if producerpv == None and producerjar == None:
            raise click.ClickException("Must specify one of --producerpv or --producerjar")

        if producerpv:
          producer = {"pv": producerpv}
        else:
          producer = {"jar" : producerjar}

        if location == None or category == None or docurl == None or edmpath == None:
            raise click.ClickException(
                    "Must specify options --location, --category, --docurl, --edmpath")

        params.value = {"producer": producer, "location": location, "category": category, "maxshelveduration": maxshelveduration, "latching": latching, "docurl": docurl, "edmpath": edmpath}

    send()

cli()
