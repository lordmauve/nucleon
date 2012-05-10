from nose.tools import eq_
from unittest import TestCase
from mock import Mock
from nucleon.amqp.message import Message


class MessageTest(TestCase):
    """Test the nucleon message class exhibits the desired API.

    """
    def setUp(self):
        self.conn = Mock([
            'exchange_declare',
            'exchange_delete',
            'exchange_bind',
            'exchange_unbind',
            'queue_declare',
            'queue_delete',
            'queue_purge',
            'queue_bind',
            'queue_unbind',
            'publish',
            'cancel',
            'basic_publish',
            'basic_cancel',
            'basic_get',
            'basic_reject',
            'basic_qos',
            'ack',
            'consume'
        ])
        self.result = {
            'body': 'hello',
            'exchange': 'messages',
            'routing_key': 'channel.foo',
            'headers': {
                'content-encoding': 'utf-8',
                'x-puka-delivery-tag': 1
                },
            'consumer_tag': 'amq.ctag-ggYz72UjKJ6pC5BWz_MUIT',
            'promise_number': 5,
            'redelivered': False,
            'delivery_tag': 1
        }
        self.msg = Message(self.conn, self.result)

    def test_subscript(self):
        """We can access attributes with subscripts"""
        eq_(self.msg['body'], 'hello')
        eq_(self.msg['delivery_tag'], 1)

    def test_body(self):
        """Body is an attribute"""
        eq_(self.msg.body, 'hello')

    def test_routing_key(self):
        """Routing key is an attribute"""
        eq_(self.msg.routing_key, 'channel.foo')

    def test_exchange(self):
        """Exchange is an attribute"""
        eq_(self.msg.exchange, 'messages')

    def test_conn_property(self):
        """Connection is an attribute"""
        assert self.msg.conn is self.conn

    def test_redelivered(self):
        """Redelivery status is an attribute"""
        eq_(self.msg.redelivered, False)

    def test_delivery_tag(self):
        """Delivery tag is an attribute"""
        eq_(self.msg.delivery_tag, 1)

    def test_consumer_tag(self):
        """Consumer tag is an attribute"""
        eq_(self.msg.consumer_tag, 'amq.ctag-ggYz72UjKJ6pC5BWz_MUIT')

    def test_ack(self):
        """We can acknowledge a message directly"""
        self.msg.ack()
        self.conn.ack.assert_called_with(self.result)

    def test_reply(self):
        """We can reply on this connection with the same routing key, and exchange"""
        self.msg.reply(body='hello to you too')
        self.conn.publish.assert_called_with(
            exchange='messages',
            routing_key='channel.foo',
            body='hello to you too'
        )

    def test_reply_different_routing_key(self):
        """We can reply on this connection with the same exchange"""
        self.msg.reply(
            routing_key='response.foo',
            body='hello to you too'
        )
        self.conn.publish.assert_called_with(
            exchange='messages',
            routing_key='response.foo',
            body='hello to you too'
        )

    def test_reply_different_exchange(self):
        """We can reply on this connection"""
        self.msg.reply(
            exchange='responses',
            routing_key='response.foo',
            body='hello to you too'
        )
        self.conn.publish.assert_called_with(
            exchange='responses',
            routing_key='response.foo',
            body='hello to you too'
        )

    def test_reply_accepts_kwargs(self):
        """We can pass arbitrary arguments to reply."""
        self.msg.reply(
            body='foo',
            bar='bar'
        )
        self.conn.publish.assert_called_with(
            exchange='messages',
            routing_key='channel.foo',
            body='foo',
            bar='bar'
        )

    def test_cancel(self):
        """We can cancel the consumer."""
        self.msg.cancel_consume()
        self.conn.basic_cancel.assert_called_with(5)

    def test_reject(self):
        """We can reject the message."""
        self.msg.reject()
        self.conn.basic_reject.assert_called_with(self.result)

    def test_reject_with_requeue(self):
        """We can reject the message."""
        self.msg.reject(requeue=True)
        self.conn.basic_reject.assert_called_with(self.result, requeue=True)
