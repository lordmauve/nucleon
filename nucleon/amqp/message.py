class Message(object):
    """A wrapper for a received AMQP message.

    This class presents an API that allows messages to be conveniently
    consumed; typical operations can be performed in the callback by accessing
    properties and calling methods of the message object.

    """

    def __init__(self, conn, result):
        """Construct a message.

        `conn` is a PukaConnection that will be used to communicate with the
        source AMQP server. `result` is the puka Frame received.

        """
        self.conn = conn
        self._frame = result

    def __getitem__(self, key):
        """Allow attributes to be read with subscript.

        This is for compatibility with the raw frame.
        """
        return self._frame[key]

    @property
    def exchange(self):
        """Retrieve the exchange."""
        return self._frame['exchange']

    @property
    def routing_key(self):
        """Retrieve the routing key."""
        return self._frame['routing_key']

    @property
    def body(self):
        """Retrieve the message body."""
        return self._frame['body']

    @property
    def redelivered(self):
        """Retrieve the redelivery status."""
        return self._frame['redelivered']

    @property
    def delivery_tag(self):
        """Retrieve the delivery tag."""
        return self._frame['delivery_tag']

    @property
    def consumer_tag(self):
        """Retrieve the consumer tag."""
        return self._frame['consumer_tag']

    def ack(self, **kwargs):
        """Acknowledge the message."""
        assert 'promise_number' in self._frame
        self.conn.ack(self._frame, **kwargs)

    def reply(self, **kwargs):
        """Publish a new message back to the connection"""
        params = {
            'exchange': self.exchange,
            'routing_key': self.routing_key
        }
        params.update(kwargs)
        self.conn.publish(**params)

    def reject(self, **kwargs):
        """Reject a message, returning it to the queue.

        Note that this doesn't mean the message won't be redelivered to this
        same client. As the spec says:

            "The client MUST NOT use this method as a means of selecting
            messages to process."

        """
        self.conn.basic_reject(self._frame, **kwargs)

    def cancel_consume(self, **kwargs):
        """Cancel the consumer."""
        self.conn.basic_cancel(self._frame['promise_number'], **kwargs)
