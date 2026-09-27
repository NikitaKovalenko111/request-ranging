package kafka

import (
	"context"
	"fmt"

	"github.com/twmb/franz-go/pkg/kgo"
)

type Client struct {
	client *kgo.Client
}

type MessageHandler interface {
	Handle(ctx context.Context, payload []byte) error
}

func New(brokers []string, consumerGroup string) (*Client, error) {
	client, err := kgo.NewClient(
		kgo.SeedBrokers(brokers...),
		kgo.ClientID("executor-balancer"),
		kgo.ConsumerGroup(consumerGroup),
		kgo.DisableAutoCommit(),
	)
	if err != nil {
		return nil, fmt.Errorf("create kafka client: %w", err)
	}
	return &Client{client: client}, nil
}

func (c *Client) Name() string { return "kafka" }

func (c *Client) Check(ctx context.Context) error {
	if err := c.client.Ping(ctx); err != nil {
		return fmt.Errorf("ping kafka: %w", err)
	}
	return nil
}

func (c *Client) Raw() *kgo.Client { return c.client }

func (c *Client) Consume(ctx context.Context, topic string, handler MessageHandler) error {
	c.client.AddConsumeTopics(topic)
	for {
		fetches := c.client.PollRecords(ctx, 100)
		if ctx.Err() != nil {
			return nil
		}
		if fetchErrors := fetches.Errors(); len(fetchErrors) > 0 {
			return fmt.Errorf("poll Kafka topic %q: %v", topic, fetchErrors[0].Err)
		}
		for _, record := range fetches.Records() {
			if err := handler.Handle(ctx, record.Value); err != nil {
				return fmt.Errorf("handle Kafka record topic=%q partition=%d offset=%d: %w",
					record.Topic, record.Partition, record.Offset, err,
				)
			}
			if err := c.client.CommitRecords(ctx, record); err != nil {
				return fmt.Errorf("commit Kafka record topic=%q partition=%d offset=%d: %w",
					record.Topic, record.Partition, record.Offset, err,
				)
			}
		}
	}
}

func (c *Client) Close() { c.client.Close() }
