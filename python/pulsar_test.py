#!/usr/bin/env python
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#


from unittest import TestCase, main
import time
import os
from pulsar import Client, MessageId, \
            CompressionType, ConsumerType, PartitionsRoutingMode, \
            AuthenticationTLS, Authentication, AuthenticationToken

from _pulsar import ProducerConfiguration, ConsumerConfiguration

try:
    # For Python 3.0 and later
    from urllib.request import urlopen, Request
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, Request


def doHttpPost(url, data):
    req = Request(url, data.encode())
    req.add_header('Content-Type', 'application/json')
    urlopen(req)


def doHttpPut(url, data):
    try:
        req = Request(url, data.encode())
        req.add_header('Content-Type', 'application/json')
        req.get_method = lambda: 'PUT'
        urlopen(req)
    except Exception as ex:
        # ignore conflicts exception to have test idempotency
        if '409' in str(ex):
            pass
        else:
            raise ex


def doHttpGet(url):
    req = Request(url)
    req.add_header('Accept', 'application/json')
    return urlopen(req).read()

class PulsarTest(TestCase):

    serviceUrl = 'pulsar://localhost:6650'
    adminUrl = 'http://localhost:8080'

    serviceUrlTls = 'pulsar+ssl://localhost:6651'

    def test_producer_config(self):
        conf = ProducerConfiguration()
        conf.send_timeout_millis(12)
        self.assertEqual(conf.send_timeout_millis(), 12)

        self.assertEqual(conf.compression_type(), CompressionType.NONE)
        conf.compression_type(CompressionType.LZ4)
        self.assertEqual(conf.compression_type(), CompressionType.LZ4)

        conf.max_pending_messages(120)
        self.assertEqual(conf.max_pending_messages(), 120)

    def test_consumer_config(self):
        conf = ConsumerConfiguration()
        self.assertEqual(conf.consumer_type(), ConsumerType.Exclusive)
        conf.consumer_type(ConsumerType.Shared)
        self.assertEqual(conf.consumer_type(), ConsumerType.Shared)

        self.assertEqual(conf.consumer_name(), '')
        conf.consumer_name("my-name")
        self.assertEqual(conf.consumer_name(), "my-name")

    def test_simple_producer(self):
        client = Client(self.serviceUrl)
        producer = client.create_producer('my-python-topic')
        producer.send(b'hello')
        producer.close()
        client.close()

    def test_producer_send_async(self):
        client = Client(self.serviceUrl)
        producer = client.create_producer('my-python-topic')

        sent_messages = []

        def send_callback(producer, msg):
            sent_messages.append(msg)

        producer.send_async(b'hello', send_callback)
        producer.send_async(b'hello', send_callback)
        producer.send_async(b'hello', send_callback)

        i = 0
        while len(sent_messages) < 3 and i < 100:
            time.sleep(0.1)
            i += 1
        self.assertEqual(len(sent_messages), 3)
        client.close()

    def test_producer_consumer(self):
        client = Client(self.serviceUrl)
        consumer = client.subscribe('my-python-topic-producer-consumer',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('my-python-topic-producer-consumer')
        producer.send(b'hello')

        msg = consumer.receive(1000)
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')

        try:
            msg = consumer.receive(100)
            self.assertTrue(False)  # Should not reach this point
        except:
            pass  # Exception is expected

        client.close()

    def test_tls_auth(self):
        certs_dir = '/pulsar/pulsar-broker/src/test/resources/authentication/tls/'
        if not os.path.exists(certs_dir):
            certs_dir = "../../pulsar-broker/src/test/resources/authentication/tls/"
        client = Client(self.serviceUrlTls,
                        tls_trust_certs_file_path=certs_dir + 'cacert.pem',
                        tls_allow_insecure_connection=False,
                        authentication=AuthenticationTLS(certs_dir + 'client-cert.pem', certs_dir + 'client-key.pem'))

        consumer = client.subscribe('my-python-topic-producer-consumer',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('my-python-topic-producer-consumer')
        producer.send(b'hello')

        msg = consumer.receive(1000)
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')

        try:
            msg = consumer.receive(100)
            self.assertTrue(False)  # Should not reach this point
        except:
            pass  # Exception is expected

        client.close()

    def test_tls_auth2(self):
        certs_dir = '/pulsar/pulsar-broker/src/test/resources/authentication/tls/'
        if not os.path.exists(certs_dir):
            certs_dir = "../../pulsar-broker/src/test/resources/authentication/tls/"
        authPlugin = "org.apache.pulsar.client.impl.auth.AuthenticationTls"
        authParams = "tlsCertFile:%s/client-cert.pem,tlsKeyFile:%s/client-key.pem" % (certs_dir, certs_dir)

        client = Client(self.serviceUrlTls,
                        tls_trust_certs_file_path=certs_dir + 'cacert.pem',
                        tls_allow_insecure_connection=False,
                        authentication=Authentication(authPlugin, authParams))

        consumer = client.subscribe('my-python-topic-producer-consumer',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('my-python-topic-producer-consumer')
        producer.send(b'hello')

        msg = consumer.receive(1000)
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')

        try:
            msg = consumer.receive(100)
            self.assertTrue(False)  # Should not reach this point
        except:
            pass  # Exception is expected

        client.close()

    def test_tls_auth3(self):
        certs_dir = '/pulsar/pulsar-broker/src/test/resources/authentication/tls/'
        if not os.path.exists(certs_dir):
            certs_dir = "../../pulsar-broker/src/test/resources/authentication/tls/"
        authPlugin = "tls"
        authParams = "tlsCertFile:%s/client-cert.pem,tlsKeyFile:%s/client-key.pem" % (certs_dir, certs_dir)

        client = Client(self.serviceUrlTls,
                        tls_trust_certs_file_path=certs_dir + 'cacert.pem',
                        tls_allow_insecure_connection=False,
                        authentication=Authentication(authPlugin, authParams))

        consumer = client.subscribe('my-python-topic-producer-consumer',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('my-python-topic-producer-consumer')
        producer.send(b'hello')

        msg = consumer.receive(1000)
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')

        try:
            msg = consumer.receive(100)
            self.assertTrue(False)  # Should not reach this point
        except:
            pass  # Exception is expected

        client.close()

    def test_auth_junk_params(self):
        certs_dir = '/pulsar/pulsar-broker/src/test/resources/authentication/tls/'
        if not os.path.exists(certs_dir):
            certs_dir = "../../pulsar-broker/src/test/resources/authentication/tls/"
        authPlugin = "someoldjunk.so"
        authParams = "blah"
        client = Client(self.serviceUrlTls,
                        tls_trust_certs_file_path=certs_dir + 'cacert.pem',
                        tls_allow_insecure_connection=False,
                        authentication=Authentication(authPlugin, authParams))
        try:
            client.subscribe('my-python-topic-producer-consumer',
                             'my-sub',
                             consumer_type=ConsumerType.Shared)
        except:
            pass  # Exception is expected

    def test_message_listener(self):
        client = Client(self.serviceUrl)

        received_messages = []

        def listener(consumer, msg):
            print("Got message: %s" % msg)
            received_messages.append(msg)
            consumer.acknowledge(msg)

        client.subscribe('my-python-topic-listener',
                         'my-sub',
                         consumer_type=ConsumerType.Exclusive,
                         message_listener=listener)
        producer = client.create_producer('my-python-topic-listener')
        producer.send(b'hello-1')
        producer.send(b'hello-2')
        producer.send(b'hello-3')

        time.sleep(0.1)
        self.assertEqual(len(received_messages), 3)
        self.assertEqual(received_messages[0].data(), b"hello-1")
        self.assertEqual(received_messages[1].data(), b"hello-2")
        self.assertEqual(received_messages[2].data(), b"hello-3")
        client.close()

    def test_reader_simple(self):
        client = Client(self.serviceUrl)
        reader = client.create_reader('my-python-topic-reader-simple',
                                      MessageId.earliest)

        producer = client.create_producer('my-python-topic-reader-simple')
        producer.send(b'hello')

        msg = reader.read_next()
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')

        try:
            msg = reader.read_next(100)
            self.assertTrue(False)  # Should not reach this point
        except:
            pass  # Exception is expected

        reader.close()
        client.close()

    def test_reader_on_last_message(self):
        client = Client(self.serviceUrl)
        producer = client.create_producer('my-python-topic-reader-on-last-message')

        for i in range(10):
            producer.send(b'hello-%d' % i)

        reader = client.create_reader('my-python-topic-reader-on-last-message',
                                      MessageId.latest)

        for i in range(10, 20):
            producer.send(b'hello-%d' % i)

        for i in range(10, 20):
            msg = reader.read_next()
            self.assertTrue(msg)
            self.assertEqual(msg.data(), b'hello-%d' % i)

        reader.close()
        client.close()

    def test_reader_on_specific_message(self):
        client = Client(self.serviceUrl)
        producer = client.create_producer(
            'my-python-topic-reader-on-specific-message')

        for i in range(10):
            producer.send(b'hello-%d' % i)

        reader1 = client.create_reader(
                'my-python-topic-reader-on-specific-message',
                MessageId.earliest)

        for i in range(5):
            msg = reader1.read_next()
            last_msg_id = msg.message_id()

        reader2 = client.create_reader(
                'my-python-topic-reader-on-specific-message',
                last_msg_id)

        for i in range(5, 10):
            msg = reader2.read_next()
            self.assertTrue(msg)
            self.assertEqual(msg.data(), b'hello-%d' % i)

        reader1.close()
        reader2.close()
        client.close()

    def test_reader_on_specific_message_with_batches(self):
        client = Client(self.serviceUrl)
        producer = client.create_producer(
            'my-python-topic-reader-on-specific-message-with-batches',
            batching_enabled=True,
            batching_max_publish_delay_ms=1000)

        for i in range(10):
            producer.send_async(b'hello-%d' % i, None)

        # Send one sync message to make sure everything was published
        producer.send(b'hello-10')

        reader1 = client.create_reader(
                'my-python-topic-reader-on-specific-message-with-batches',
                MessageId.earliest)

        for i in range(5):
            msg = reader1.read_next()
            last_msg_id = msg.message_id()

        reader2 = client.create_reader(
                'my-python-topic-reader-on-specific-message-with-batches',
                last_msg_id)

        for i in range(5, 11):
            msg = reader2.read_next()
            self.assertTrue(msg)
            self.assertEqual(msg.data(), b'hello-%d' % i)

        reader1.close()
        reader2.close()
        client.close()

    def test_producer_sequence_after_reconnection(self):
        # Enable deduplication on namespace
        doHttpPost(self.adminUrl + '/admin/v2/namespaces/public/default/deduplication',
                   'true')
        client = Client(self.serviceUrl)

        topic = 'my-python-test-producer-sequence-after-reconnection-' \
            + str(time.time())

        producer = client.create_producer(topic, producer_name='my-producer-name')
        self.assertEqual(producer.last_sequence_id(), -1)

        for i in range(10):
            producer.send(b'hello-%d' % i)
            self.assertEqual(producer.last_sequence_id(), i)

        producer.close()

        producer = client.create_producer(topic, producer_name='my-producer-name')
        self.assertEqual(producer.last_sequence_id(), 9)

        for i in range(10, 20):
            producer.send(b'hello-%d' % i)
            self.assertEqual(producer.last_sequence_id(), i)

        doHttpPost(self.adminUrl + '/admin/v2/namespaces/public/default/deduplication',
                   'false')

    def test_producer_deduplication(self):
        # Enable deduplication on namespace
        doHttpPost(self.adminUrl + '/admin/v2/namespaces/public/default/deduplication',
                   'true')
        client = Client(self.serviceUrl)

        topic = 'my-python-test-producer-deduplication-' + str(time.time())

        producer = client.create_producer(topic, producer_name='my-producer-name')
        self.assertEqual(producer.last_sequence_id(), -1)

        consumer = client.subscribe(topic, 'my-sub')

        producer.send(b'hello-0', sequence_id=0)
        producer.send(b'hello-1', sequence_id=1)
        producer.send(b'hello-2', sequence_id=2)
        self.assertEqual(producer.last_sequence_id(), 2)

        # Repeat the messages and verify they're not received by consumer
        producer.send(b'hello-1', sequence_id=1)
        producer.send(b'hello-2', sequence_id=2)
        self.assertEqual(producer.last_sequence_id(), 2)

        for i in range(3):
            msg = consumer.receive()
            self.assertEqual(msg.data(), b'hello-%d' % i)
            consumer.acknowledge(msg)

        try:
            # No other messages should be received
            consumer.receive(timeout_millis=1000)
            self.assertTrue(False)
        except:
            # Exception is expected
            pass

        producer.close()

        producer = client.create_producer(topic, producer_name='my-producer-name')
        self.assertEqual(producer.last_sequence_id(), 2)

        # Repeat the messages and verify they're not received by consumer
        producer.send(b'hello-1', sequence_id=1)
        producer.send(b'hello-2', sequence_id=2)
        self.assertEqual(producer.last_sequence_id(), 2)

        try:
            # No other messages should be received
            consumer.receive(timeout_millis=1000)
            self.assertTrue(False)
        except:
            # Exception is expected
            pass

        doHttpPost(self.adminUrl + '/admin/v2/namespaces/public/default/deduplication',
                   'false')

    def test_producer_routing_mode(self):
        client = Client(self.serviceUrl)
        producer = client.create_producer('my-python-test-producer',
                                          message_routing_mode=PartitionsRoutingMode.UseSinglePartition)
        producer.send(b'test')
        client.close()

    def test_message_argument_errors(self):
        client = Client(self.serviceUrl)
        topic = 'my-python-test-producer'
        producer = client.create_producer(topic)

        content = 'test'.encode('utf-8')

        self._check_value_error(lambda: producer.send(5))
        self._check_value_error(lambda: producer.send(content, properties='test'))
        self._check_value_error(lambda: producer.send(content, partition_key=5))
        self._check_value_error(lambda: producer.send(content, sequence_id='test'))
        self._check_value_error(lambda: producer.send(content, replication_clusters=5))
        self._check_value_error(lambda: producer.send(content, disable_replication='test'))
        client.close()

    def test_client_argument_errors(self):
        self._check_value_error(lambda: Client(None))
        self._check_value_error(lambda: Client(self.serviceUrl, authentication="test"))
        self._check_value_error(lambda: Client(self.serviceUrl, operation_timeout_seconds="test"))
        self._check_value_error(lambda: Client(self.serviceUrl, io_threads="test"))
        self._check_value_error(lambda: Client(self.serviceUrl, message_listener_threads="test"))
        self._check_value_error(lambda: Client(self.serviceUrl, concurrent_lookup_requests="test"))
        self._check_value_error(lambda: Client(self.serviceUrl, log_conf_file_path=5))
        self._check_value_error(lambda: Client(self.serviceUrl, use_tls="test"))
        self._check_value_error(lambda: Client(self.serviceUrl, tls_trust_certs_file_path=5))
        self._check_value_error(lambda: Client(self.serviceUrl, tls_allow_insecure_connection="test"))

    def test_producer_argument_errors(self):
        client = Client(self.serviceUrl)

        self._check_value_error(lambda: client.create_producer(None))

        topic = 'my-python-test-producer'

        self._check_value_error(lambda: client.create_producer(topic, producer_name=5))
        self._check_value_error(lambda: client.create_producer(topic, initial_sequence_id='test'))
        self._check_value_error(lambda: client.create_producer(topic, send_timeout_millis='test'))
        self._check_value_error(lambda: client.create_producer(topic, compression_type=None))
        self._check_value_error(lambda: client.create_producer(topic, max_pending_messages='test'))
        self._check_value_error(lambda: client.create_producer(topic, block_if_queue_full='test'))
        self._check_value_error(lambda: client.create_producer(topic, batching_enabled='test'))
        self._check_value_error(lambda: client.create_producer(topic, batching_enabled='test'))
        self._check_value_error(lambda: client.create_producer(topic, batching_max_allowed_size_in_bytes='test'))
        self._check_value_error(lambda: client.create_producer(topic, batching_max_publish_delay_ms='test'))
        client.close()

    def test_consumer_argument_errors(self):
        client = Client(self.serviceUrl)

        topic = 'my-python-test-producer'
        sub_name = 'my-sub-name'

        self._check_value_error(lambda: client.subscribe(None, sub_name))
        self._check_value_error(lambda: client.subscribe(topic, None))
        self._check_value_error(lambda: client.subscribe(topic, sub_name, consumer_type=None))
        self._check_value_error(lambda: client.subscribe(topic, sub_name, receiver_queue_size='test'))
        self._check_value_error(lambda: client.subscribe(topic, sub_name, consumer_name=5))
        self._check_value_error(lambda: client.subscribe(topic, sub_name, unacked_messages_timeout_ms='test'))
        self._check_value_error(lambda: client.subscribe(topic, sub_name, broker_consumer_stats_cache_time_ms='test'))
        client.close()

    def test_reader_argument_errors(self):
        client = Client(self.serviceUrl)
        topic = 'my-python-test-producer'

        # This should not raise exception
        client.create_reader(topic, MessageId.earliest)

        self._check_value_error(lambda: client.create_reader(None, MessageId.earliest))
        self._check_value_error(lambda: client.create_reader(topic, None))
        self._check_value_error(lambda: client.create_reader(topic, MessageId.earliest, receiver_queue_size='test'))
        self._check_value_error(lambda: client.create_reader(topic, MessageId.earliest, reader_name=5))
        client.close()

    def test_publish_compact_and_consume(self):
        client = Client(self.serviceUrl)
        topic = 'my-python-test_publish_compact_and_consume'
        producer = client.create_producer(topic, producer_name='my-producer-name', batching_enabled=False)
        self.assertEqual(producer.last_sequence_id(), -1)
        consumer = client.subscribe(topic, 'my-sub1', is_read_compacted=True)
        consumer.close()
        consumer2 = client.subscribe(topic, 'my-sub2', is_read_compacted=False)

        # producer create 2 messages with same key.
        producer.send(b'hello-0', partition_key='key0')
        producer.send(b'hello-1', partition_key='key0')
        producer.close()

        # issue compact command, and wait success
        url=self.adminUrl + '/admin/v2/persistent/public/default/my-python-test_publish_compact_and_consume/compaction'
        doHttpPut(url, '')
        while True:
            s=doHttpGet(url).decode('utf-8')
            if 'RUNNING' in s:
                print("Compact still running")
                print(s)
                time.sleep(0.2)
            else:
                self.assertTrue('SUCCESS' in s)
                print("Compact Complete now")
                print(s)
                break

        # after compact, consumer with `is_read_compacted=True`, expected read only the second message for same key.
        consumer1 = client.subscribe(topic, 'my-sub1', is_read_compacted=True)
        msg0 = consumer1.receive()
        self.assertEqual(msg0.data(), b'hello-1')
        consumer1.acknowledge(msg0)
        consumer1.close()

        # after compact, consumer with `is_read_compacted=False`, expected read 2 messages for same key.
        msg0 = consumer2.receive()
        self.assertEqual(msg0.data(), b'hello-0')
        consumer2.acknowledge(msg0)
        msg1 = consumer2.receive()
        self.assertEqual(msg1.data(), b'hello-1')
        consumer2.acknowledge(msg1)
        consumer2.close()
        client.close()

    def test_reader_has_message_available(self):
        # create client, producer, reader
        client = Client(self.serviceUrl)
        producer = client.create_producer('my-python-topic-reader-has-message-available')
        reader = client.create_reader('my-python-topic-reader-has-message-available',
                                      MessageId.latest)

        # before produce data, expected not has message available
        self.assertFalse(reader.has_message_available());

        for i in range(10):
            producer.send(b'hello-%d' % i)

        # produced data, expected has message available
        self.assertTrue(reader.has_message_available());

        for i in range(10):
            msg = reader.read_next()
            self.assertTrue(msg)
            self.assertEqual(msg.data(), b'hello-%d' % i)

        # consumed all data, expected not has message available
        self.assertFalse(reader.has_message_available());

        for i in range(10, 20):
            producer.send(b'hello-%d' % i)

        # produced data again, expected has message available
        self.assertTrue(reader.has_message_available());
        reader.close()
        producer.close()
        client.close()

    def test_seek(self):
        client = Client(self.serviceUrl)
        consumer = client.subscribe('my-python-topic-seek',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('my-python-topic-seek')

        for i in range(100):
            producer.send(b'hello-%d' % i)

        for i in range(100):
            msg = consumer.receive()
            self.assertEqual(msg.data(), b'hello-%d' % i)
            consumer.acknowledge(msg)

        # seek, and after reconnect, expected receive first message.
        consumer.seek(MessageId.earliest)
        time.sleep(0.5)
        msg = consumer.receive()
        self.assertEqual(msg.data(), b'hello-0')
        client.close()

    def test_v2_topics(self):
        self._v2_topics(self.serviceUrl)

    def test_v2_topics_http(self):
        self._v2_topics(self.adminUrl)

    def _v2_topics(self, url):
        client = Client(url)
        consumer = client.subscribe('my-v2-topic-producer-consumer',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('my-v2-topic-producer-consumer')
        producer.send(b'hello')

        msg = consumer.receive(1000)
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')
        consumer.acknowledge(msg)

        try:
            msg = consumer.receive(100)
            self.assertTrue(False)  # Should not reach this point
        except:
            pass  # Exception is expected

        client.close()

    def test_topics_consumer(self):
        client = Client(self.serviceUrl)
        topic1 = 'persistent://public/default/my-python-topics-consumer-1'
        topic2 = 'persistent://public/default/my-python-topics-consumer-2'
        topic3 = 'persistent://public/default/my-python-topics-consumer-3'
        topics = [topic1, topic2, topic3]

        url1 = self.adminUrl + '/admin/v2/persistent/public/default/my-python-topics-consumer-1/partitions'
        url2 = self.adminUrl + '/admin/v2/persistent/public/default/my-python-topics-consumer-2/partitions'
        url3 = self.adminUrl + '/admin/v2/persistent/public/default/my-python-topics-consumer-3/partitions'

        doHttpPut(url1, '2')
        doHttpPut(url2, '3')
        doHttpPut(url3, '4')

        producer1 = client.create_producer(topic1)
        producer2 = client.create_producer(topic2)
        producer3 = client.create_producer(topic3)

        consumer = client.subscribe(topics,
                                    'my-topics-consumer-sub',
                                    consumer_type=ConsumerType.Shared,
                                    receiver_queue_size=10
                                    )

        for i in range(100):
            producer1.send(b'hello-1-%d' % i)

        for i in range(100):
            producer2.send(b'hello-2-%d' % i)

        for i in range(100):
            producer3.send(b'hello-3-%d' % i)


        for i in range(300):
            msg = consumer.receive()
            consumer.acknowledge(msg)

        try:
        # No other messages should be received
            consumer.receive(timeout_millis=500)
            self.assertTrue(False)
        except:
            # Exception is expected
            pass
        client.close()

    def test_topics_pattern_consumer(self):
        import re
        client = Client(self.serviceUrl)

        topics_pattern = 'persistent://public/default/my-python-pattern-consumer.*'

        topic1 = 'persistent://public/default/my-python-pattern-consumer-1'
        topic2 = 'persistent://public/default/my-python-pattern-consumer-2'
        topic3 = 'persistent://public/default/my-python-pattern-consumer-3'

        url1 = self.adminUrl + '/admin/v2/persistent/public/default/my-python-pattern-consumer-1/partitions'
        url2 = self.adminUrl + '/admin/v2/persistent/public/default/my-python-pattern-consumer-2/partitions'
        url3 = self.adminUrl + '/admin/v2/persistent/public/default/my-python-pattern-consumer-3/partitions'

        doHttpPut(url1, '2')
        doHttpPut(url2, '3')
        doHttpPut(url3, '4')

        producer1 = client.create_producer(topic1)
        producer2 = client.create_producer(topic2)
        producer3 = client.create_producer(topic3)

        consumer = client.subscribe(re.compile(topics_pattern),
                                    'my-pattern-consumer-sub',
                                    consumer_type = ConsumerType.Shared,
                                    receiver_queue_size = 10,
                                    pattern_auto_discovery_period = 1
                                   )

        # wait enough time to trigger auto discovery
        time.sleep(2)

        for i in range(100):
            producer1.send(b'hello-1-%d' % i)

        for i in range(100):
            producer2.send(b'hello-2-%d' % i)

        for i in range(100):
            producer3.send(b'hello-3-%d' % i)


        for i in range(300):
            msg = consumer.receive()
            consumer.acknowledge(msg)

        try:
            # No other messages should be received
            consumer.receive(timeout_millis=500)
            self.assertTrue(False)
        except:
            # Exception is expected
            pass
        client.close()

    def test_message_id(self):
        s = MessageId.earliest.serialize()
        self.assertEqual(MessageId.deserialize(s), MessageId.earliest)

        s = MessageId.latest.serialize()
        self.assertEqual(MessageId.deserialize(s), MessageId.latest)

    def test_get_topics_partitions(self):
        client = Client(self.serviceUrl)
        topic_partitioned = 'persistent://public/default/test_get_topics_partitions'
        topic_non_partitioned = 'persistent://public/default/test_get_topics_not-partitioned'

        url1 = self.adminUrl + '/admin/v2/persistent/public/default/test_get_topics_partitions/partitions'
        doHttpPut(url1, '3')

        self.assertEqual(client.get_topic_partitions(topic_partitioned),
                         ['persistent://public/default/test_get_topics_partitions-partition-0',
                          'persistent://public/default/test_get_topics_partitions-partition-1',
                          'persistent://public/default/test_get_topics_partitions-partition-2'])

        self.assertEqual(client.get_topic_partitions(topic_non_partitioned),
                         [topic_non_partitioned])
        client.close()

    def test_token_auth(self):
        with open('/tmp/pulsar-test-data/tokens/token.txt') as tf:
            token = tf.read().strip()

        # Use adminUrl to test both HTTP request and binary protocol
        client = Client(self.adminUrl,
                        authentication=AuthenticationToken(token))

        consumer = client.subscribe('persistent://private/auth/my-python-topic-token-auth',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('persistent://private/auth/my-python-topic-token-auth')
        producer.send(b'hello')

        msg = consumer.receive(1000)
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')
        client.close()

    def test_token_auth_supplier(self):
        def read_token():
            with open('/tmp/pulsar-test-data/tokens/token.txt') as tf:
                return tf.read().strip()

        client = Client(self.serviceUrl,
                        authentication=AuthenticationToken(read_token))
        consumer = client.subscribe('persistent://private/auth/my-python-topic-token-auth',
                                    'my-sub',
                                    consumer_type=ConsumerType.Shared)
        producer = client.create_producer('persistent://private/auth/my-python-topic-token-auth')
        producer.send(b'hello')

        msg = consumer.receive(1000)
        self.assertTrue(msg)
        self.assertEqual(msg.data(), b'hello')
        client.close()

    #####

    def _check_value_error(self, fun):
        try:
            fun()
            # Should throw exception
            self.assertTrue(False)
        except ValueError:
            pass  # Expected


if __name__ == '__main__':
    main()
