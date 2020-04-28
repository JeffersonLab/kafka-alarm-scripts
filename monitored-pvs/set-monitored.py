from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer


value_schema_str = """
{
   "namespace": "org.jlab",
   "name": "MonitoredPV",
   "type": "record",
   "fields" : [
     {
       "name" : "name",
       "type" : "string"
     },
     {
       "name" : "topic",
       "type" : "string"
     }
   ]
}
"""

key_schema_str = """
{
   "namespace": "org.jlab",
   "name": "MonitoredPV",
   "type": "record",
   "fields" : [
     {
       "name" : "name",
       "type" : "string"
     }
   ]
}
"""

value_schema = avro.loads(value_schema_str)
key_schema = avro.loads(key_schema_str)
value = {"name": "iocin1:heartbeat", "topic": "iocin1-heartbeat"}
key = {"name": "iocin1:heartbeat"}


def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))


avroProducer = AvroProducer({
    'bootstrap.servers': 'localhost',
    'on_delivery': delivery_report,
    'schema.registry.url': 'http://localhost:8081'
    }, default_key_schema=key_schema, default_value_schema=value_schema)

avroProducer.produce(topic='monitored-pvs', value=value, key=key)
avroProducer.flush()
