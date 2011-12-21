#!/usr/bin/env python
import puka
import sys

if len(sys.argv) <= 2:
    print "Please specify routing_key and message to send"
    print "%s [routing_key] [message]" % sys.argv[0]
    sys.exit(1)

client = puka.Client("amqp:///")
promise = client.connect()
client.wait(promise)

exchange = 'test_room'
message = sys.argv[2]
routing_key = sys.argv[1]

#promise = client.queue_declare(queue='hello')
#client.wait(promise)

promise = client.basic_publish(exchange=exchange,
                               routing_key=routing_key,
                               body=message)
client.wait(promise)



print "Sent: '%s' to exchange: '%s' using routing_key: '%s'" % (message, exchange, routing_key)
client.close()
