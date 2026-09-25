package kafka

import (
	"context"
	"fmt"

	"github.com/twmb/franz-go/pkg/kgo"
)

type Client struct {
	client *kgo.Client
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

func (c *Client) Close() { c.client.Close() }
