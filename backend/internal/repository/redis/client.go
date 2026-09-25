package redis

import (
	"context"
	"fmt"

	redisclient "github.com/redis/go-redis/v9"
)

type Client struct {
	client *redisclient.Client
}

func New(address string) *Client {
	client := redisclient.NewClient(&redisclient.Options{
		Addr:       address,
		MaxRetries: -1,
	})
	return &Client{client: client}
}

func (c *Client) Name() string { return "redis" }

func (c *Client) Check(ctx context.Context) error {
	if err := c.client.Ping(ctx).Err(); err != nil {
		return fmt.Errorf("ping redis: %w", err)
	}
	return nil
}

func (c *Client) Raw() *redisclient.Client { return c.client }

func (c *Client) Close() error { return c.client.Close() }
