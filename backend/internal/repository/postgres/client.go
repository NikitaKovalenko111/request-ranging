package postgres

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

type Client struct {
	database *sql.DB
}

func New(dsn string) (*Client, error) {
	database, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}
	database.SetMaxOpenConns(20)
	database.SetMaxIdleConns(5)
	database.SetConnMaxIdleTime(5 * time.Minute)
	database.SetConnMaxLifetime(30 * time.Minute)
	return &Client{database: database}, nil
}

func (c *Client) Name() string { return "postgres" }

func (c *Client) Check(ctx context.Context) error {
	if err := c.database.PingContext(ctx); err != nil {
		return fmt.Errorf("ping postgres: %w", err)
	}
	return nil
}

func (c *Client) DB() *sql.DB { return c.database }

func (c *Client) Close() error { return c.database.Close() }
