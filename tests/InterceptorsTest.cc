/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
#include <gtest/gtest.h>
#include <pulsar/Client.h>
#include <pulsar/ProducerInterceptor.h>

#include <utility>

#include "HttpHelper.h"
#include "Latch.h"

static const std::string serviceUrl = "pulsar://localhost:6650";
static const std::string adminUrl = "http://localhost:8080/";

using namespace pulsar;

class TestInterceptor : public ProducerInterceptor {
   public:
    TestInterceptor(Latch& latch, Latch& closeLatch) : latch_(latch), closeLatch_(closeLatch) {}

    Message beforeSend(const Producer& producer, const Message& message) override {
        return MessageBuilder().setProperty("key", "set").setContent(message.getDataAsString()).build();
    }

    void onSendAcknowledgement(const Producer& producer, Result result, const Message& message,
                               const MessageId& messageID) override {
        ASSERT_EQ(result, ResultOk);
        auto properties = message.getProperties();
        ASSERT_TRUE(properties.find("key") != properties.end() && properties["key"] == "set");
        latch_.countdown();
    }

    void close() override { closeLatch_.countdown(); }

   private:
    Latch latch_;
    Latch closeLatch_;
};

class ExceptionInterceptor : public ProducerInterceptor {
   public:
    explicit ExceptionInterceptor(Latch& latch) : latch_(latch) {}

    Message beforeSend(const Producer& producer, const Message& message) override {
        latch_.countdown();
        throw std::runtime_error("expected exception");
    }

    void onSendAcknowledgement(const Producer& producer, Result result, const Message& message,
                               const MessageId& messageID) override {
        latch_.countdown();
        throw std::runtime_error("expected exception");
    }

    void close() override {
        latch_.countdown();
        throw std::runtime_error("expected exception");
    }

   private:
    Latch latch_;
};

class PartitionsChangeInterceptor : public ProducerInterceptor {
   public:
    explicit PartitionsChangeInterceptor(Latch& latch) : latch_(latch) {}

    Message beforeSend(const Producer& producer, const Message& message) override { return message; }

    void onSendAcknowledgement(const Producer& producer, Result result, const Message& message,
                               const MessageId& messageID) override {}

    void onPartitionsChange(const std::string& topicName, int partitions) override {
        ASSERT_EQ(partitions, 3);
        latch_.countdown();
    }

   private:
    Latch latch_;
};

void createPartitionedTopic(std::string topic) {
    std::string topicOperateUrl = adminUrl + "admin/v2/persistent/public/default/" + topic + "/partitions";

    int res = makePutRequest(topicOperateUrl, "2");
    ASSERT_TRUE(res == 204 || res == 409) << "res: " << res;
}

class InterceptorsTest : public ::testing::TestWithParam<bool> {};

TEST_P(InterceptorsTest, testProducerInterceptor) {
    const std::string topic = "InterceptorsTest-testProducerInterceptor-" + std::to_string(time(nullptr));

    if (GetParam()) {
        createPartitionedTopic(topic);
    }

    Latch latch(1);
    Latch closeLatch(1);

    Client client(serviceUrl);
    ProducerConfiguration conf;
    conf.intercept({std::make_shared<TestInterceptor>(latch, closeLatch)});
    Producer producer;
    client.createProducer(topic, conf, producer);

    Message msg = MessageBuilder().setContent("content").build();
    Result result = producer.send(msg);
    ASSERT_EQ(result, ResultOk);

    ASSERT_TRUE(latch.wait(std::chrono::seconds(5)));

    producer.close();
    ASSERT_TRUE(closeLatch.wait(std::chrono::seconds(5)));
    client.close();
}

TEST_P(InterceptorsTest, testProducerInterceptorWithException) {
    const std::string topic =
        "InterceptorsTest-testProducerInterceptorWithException-" + std::to_string(time(nullptr));

    if (GetParam()) {
        createPartitionedTopic(topic);
    }

    Latch latch(3);

    Client client(serviceUrl);
    ProducerConfiguration conf;
    conf.intercept({std::make_shared<ExceptionInterceptor>(latch)});
    Producer producer;
    client.createProducer(topic, conf, producer);

    Message msg = MessageBuilder().setContent("content").build();
    Result result = producer.send(msg);
    ASSERT_EQ(result, ResultOk);

    producer.close();
    ASSERT_TRUE(latch.wait(std::chrono::seconds(5)));
    client.close();
}

TEST(InterceptorsTest, testProducerInterceptorOnPartitionsChange) {
    const std::string topic = "public/default/InterceptorsTest-testProducerInterceptorOnPartitionsChange-" +
                              std::to_string(time(nullptr));
    std::string topicOperateUrl = adminUrl + "admin/v2/persistent/" + topic + "/partitions";

    int res = makePutRequest(topicOperateUrl, "2");
    ASSERT_TRUE(res == 204 || res == 409) << "res: " << res;

    Latch latch(1);

    ClientConfiguration clientConf;
    clientConf.setPartititionsUpdateInterval(1);
    Client client(serviceUrl, clientConf);
    ProducerConfiguration conf;
    conf.intercept({std::make_shared<PartitionsChangeInterceptor>(latch)});
    Producer producer;
    client.createProducer(topic, conf, producer);

    res = makePostRequest(topicOperateUrl, "3");  // update partitions to 3
    ASSERT_TRUE(res == 204 || res == 409) << "res: " << res;

    ASSERT_TRUE(latch.wait(std::chrono::seconds(5)));

    producer.close();
    client.close();
}

INSTANTIATE_TEST_CASE_P(Pulsar, InterceptorsTest, ::testing::Values(true, false));
