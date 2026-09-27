package main

import (
	"testing"
	"time"
)

func TestUntilNextUTCMidnight(t *testing.T) {
	value := time.Date(2026, 9, 27, 21, 30, 0, 0, time.FixedZone("UTC+5", 5*60*60))
	if got, want := untilNextUTCMidnight(value), 7*time.Hour+30*time.Minute; got != want {
		t.Fatalf("untilNextUTCMidnight() = %s, want %s", got, want)
	}
}
