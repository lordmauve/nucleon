#!/usr/bin/env python
import puka
import sys

client = puka.Client("amqp:///")
promise = client.connect()
client.wait(promise)


promise = client.queue_declare(queue='hello')
client.wait(promise)

promise = client.basic_publish(exchange='test_room',
                               routing_key='listener',
                               body=sys.argv[1])
client.wait(promise)

print "Sent: '%s'" % sys.argv[1]
client.close()
