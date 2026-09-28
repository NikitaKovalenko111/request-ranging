package kafka

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"sync"
	"time"

	"github.com/twmb/franz-go/pkg/kgo"
)

type Client struct {
	client *kgo.Client
	name   string
}

type MessageHandler interface {
	Handle(ctx context.Context, payload []byte) error
}

func New(brokers []string, consumerGroup string) (*Client, error) {
	return NewNamed(brokers, consumerGroup, "executor-balancer", "kafka")
}

func NewNamed(brokers []string, consumerGroup, clientID, name string) (*Client, error) {
	client, err := kgo.NewClient(
		kgo.SeedBrokers(brokers...),
		kgo.ClientID(clientID),
		kgo.ConsumerGroup(consumerGroup),
		kgo.DisableAutoCommit(),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtStart()),
	)
	if err != nil {
		return nil, fmt.Errorf("create kafka client: %w", err)
	}
	return &Client{client: client, name: name}, nil
}

func (c *Client) Name() string { return c.name }

func (c *Client) Check(ctx context.Context) error {
	if err := c.client.Ping(ctx); err != nil {
		return fmt.Errorf("ping kafka: %w", err)
	}
	return nil
}

func (c *Client) Raw() *kgo.Client { return c.client }

func (c *Client) Consume(ctx context.Context, handlers map[string]MessageHandler, deadLetterTopic string) error {
	if len(handlers) == 0 {
		return fmt.Errorf("consume Kafka: at least one topic handler is required")
	}
	topics := make([]string, 0, len(handlers))
	for topic := range handlers {
		topics = append(topics, topic)
	}
	sort.Strings(topics)
	c.client.AddConsumeTopics(topics...)
	for {
		fetches := c.client.PollRecords(ctx, 100)
		if ctx.Err() != nil {
			return nil
		}
		if fetchErrors := fetches.Errors(); len(fetchErrors) > 0 {
			return fmt.Errorf("poll Kafka: %v", fetchErrors[0].Err)
		}
		for _, record := range fetches.Records() {
			handler, ok := handlers[record.Topic]
			if !ok {
				return fmt.Errorf("no handler configured for Kafka topic %q", record.Topic)
			}
			if err := c.processRecord(ctx, handler, deadLetterTopic, record); err != nil {
				if ctx.Err() != nil {
					return nil
				}
				return err
			}
			if commitErr := c.client.CommitRecords(ctx, record); commitErr != nil {
				return fmt.Errorf("commit Kafka record topic=%q partition=%d offset=%d: %w",
					record.Topic, record.Partition, record.Offset, commitErr,
				)
			}
		}
	}
}

// ConsumeConcurrent processes a fetched batch in parallel and commits it only
// after every record has completed. A crash can redeliver the whole batch;
// handlers therefore remain idempotent.
func (c *Client) ConsumeConcurrent(
	ctx context.Context,
	handlers map[string]MessageHandler,
	deadLetterTopic string,
	workers int,
) error {
	if len(handlers) == 0 {
		return fmt.Errorf("consume Kafka: at least one topic handler is required")
	}
	if workers <= 0 {
		return fmt.Errorf("consume Kafka: workers must be positive")
	}
	topics := make([]string, 0, len(handlers))
	for topic := range handlers {
		topics = append(topics, topic)
	}
	sort.Strings(topics)
	c.client.AddConsumeTopics(topics...)

	for {
		fetches := c.client.PollRecords(ctx, workers)
		if ctx.Err() != nil {
			return nil
		}
		if fetchErrors := fetches.Errors(); len(fetchErrors) > 0 {
			return fmt.Errorf("poll Kafka: %v", fetchErrors[0].Err)
		}
		records := fetches.Records()
		if len(records) == 0 {
			continue
		}

		errorsChannel := make(chan error, len(records))
		var waitGroup sync.WaitGroup
		for _, record := range records {
			handler, ok := handlers[record.Topic]
			if !ok {
				return fmt.Errorf("no handler configured for Kafka topic %q", record.Topic)
			}
			waitGroup.Add(1)
			go func(record *kgo.Record, handler MessageHandler) {
				defer waitGroup.Done()
				errorsChannel <- c.processRecord(ctx, handler, deadLetterTopic, record)
			}(record, handler)
		}
		waitGroup.Wait()
		close(errorsChannel)
		for processingError := range errorsChannel {
			if processingError != nil {
				if ctx.Err() != nil {
					return nil
				}
				return processingError
			}
		}
		if commitErr := c.client.CommitRecords(ctx, records...); commitErr != nil {
			return fmt.Errorf("commit concurrent Kafka batch: %w", commitErr)
		}
	}
}

func (c *Client) processRecord(
	ctx context.Context,
	handler MessageHandler,
	deadLetterTopic string,
	record *kgo.Record,
) error {
	backoff := 250 * time.Millisecond
	for {
		err := handler.Handle(ctx, record.Value)
		if err == nil {
			return nil
		}
		permanent := new(PermanentError)
		if errors.As(err, &permanent) {
			if dlqErr := c.sendDeadLetter(ctx, deadLetterTopic, record, err); dlqErr != nil {
				return dlqErr
			}
			return nil
		}
		if err := waitForRetry(ctx, backoff); err != nil {
			return err
		}
		if backoff < 5*time.Second {
			backoff *= 2
			if backoff > 5*time.Second {
				backoff = 5 * time.Second
			}
		}
	}
}

func waitForRetry(ctx context.Context, delay time.Duration) error {
	timer := time.NewTimer(delay)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

func (c *Client) sendDeadLetter(ctx context.Context, topic string, source *kgo.Record, processingError error) error {
	if topic == "" {
		return fmt.Errorf("dead-letter topic must not be empty")
	}
	payload, err := json.Marshal(map[string]any{
		"source_topic": source.Topic,
		"partition":    source.Partition,
		"offset":       source.Offset,
		"key":          string(source.Key),
		"payload":      string(source.Value),
		"error":        processingError.Error(),
		"failed_at":    time.Now().UTC(),
	})
	if err != nil {
		return fmt.Errorf("encode dead-letter record: %w", err)
	}
	result := c.client.ProduceSync(ctx, &kgo.Record{Topic: topic, Key: source.Key, Value: payload})
	if err := result.FirstErr(); err != nil {
		return fmt.Errorf("publish dead-letter record: %w", err)
	}
	return nil
}

func (c *Client) Close() { c.client.Close() }
