// Package leaderboard demonstrates bounded DISPLAY snapshots, not award settlement.
package leaderboard

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"sync"
	"time"
)

const MaxRows = 1000 // Example guard, not a product capacity recommendation.

var (
	ErrUnavailable   = errors.New("leaderboard snapshot unavailable")
	ErrCursorVersion = errors.New("cursor belongs to another snapshot")
)

type Entry struct {
	UID   int64 `json:"uid,string"`
	Power int64 `json:"power,string"` // Do not round int64 scores through float64/JavaScript numbers.
}

type Snapshot struct {
	Version    string    `json:"version"`
	CapturedAt time.Time `json:"captured_at"`
	ExpiresAt  time.Time `json:"expires_at"`
	Entries    []Entry   `json:"entries"`
}

func (s Snapshot) Validate(now time.Time) error {
	if s.Version == "" || s.CapturedAt.IsZero() || s.CapturedAt.After(now) || !s.ExpiresAt.After(now) ||
		!s.ExpiresAt.After(s.CapturedAt) || len(s.Entries) > MaxRows {
		return ErrUnavailable
	}
	seen := make(map[int64]bool)
	for i, entry := range s.Entries {
		if entry.UID <= 0 || entry.Power < 0 || seen[entry.UID] {
			return ErrUnavailable
		}
		seen[entry.UID] = true
		if i > 0 {
			previous := s.Entries[i-1]
			if previous.Power < entry.Power || (previous.Power == entry.Power && previous.UID >= entry.UID) {
				return fmt.Errorf("invalid total order: %w", ErrUnavailable)
			}
		}
	}
	return nil
}

func clone(s Snapshot) Snapshot {
	s.Entries = append([]Entry{}, s.Entries...)
	return s
}

type Cursor struct {
	Version    string
	UID, Power int64
}

// Page traverses one immutable TopN snapshot. It cannot address ranks outside TopN.
func Page(s Snapshot, cursor *Cursor, limit int) ([]Entry, *Cursor, error) {
	if limit < 1 || limit > MaxRows {
		return nil, nil, errors.New("invalid page limit")
	}
	start := 0
	if cursor != nil {
		if cursor.Version != s.Version {
			return nil, nil, ErrCursorVersion
		}
		found := false
		for i, entry := range s.Entries {
			if entry.UID == cursor.UID && entry.Power == cursor.Power {
				start, found = i+1, true
				break
			}
		}
		if !found {
			return nil, nil, errors.New("invalid cursor position")
		}
	}
	end := start + limit
	if end > len(s.Entries) {
		end = len(s.Entries)
	}
	rows := append([]Entry{}, s.Entries[start:end]...)
	var next *Cursor
	if end < len(s.Entries) {
		last := rows[len(rows)-1]
		next = &Cursor{Version: s.Version, UID: last.UID, Power: last.Power}
	}
	return rows, next, nil
}

type LoadRows func(context.Context) ([]Entry, error)
type PublishSnapshot func(context.Context, Snapshot) error

type Publisher struct {
	load    LoadRows
	publish PublishSnapshot
	ttl     time.Duration
	gate    chan struct{}
	now     func() time.Time
}

func NewPublisher(load LoadRows, publish PublishSnapshot, ttl time.Duration) (*Publisher, error) {
	if load == nil || publish == nil || ttl <= 0 {
		return nil, errors.New("invalid publisher configuration")
	}
	return &Publisher{load: load, publish: publish, ttl: ttl, gate: make(chan struct{}, 1), now: time.Now}, nil
}

// One publisher process per key: this gate does NOT coordinate multiple processes.
func (p *Publisher) Refresh(ctx context.Context) error {
	select {
	case p.gate <- struct{}{}:
	case <-ctx.Done():
		return ctx.Err()
	}
	defer func() { <-p.gate }()
	captured := p.now() // Include DB read time in the source-age budget.
	rows, err := p.load(ctx)
	if err != nil {
		return err
	} // Never publish partially scanned rows.
	var id [16]byte
	if _, err = rand.Read(id[:]); err != nil {
		return err
	}
	snapshot := Snapshot{Version: hex.EncodeToString(id[:]), CapturedAt: captured,
		ExpiresAt: captured.Add(p.ttl), Entries: append([]Entry{}, rows...)}
	if err = snapshot.Validate(p.now()); err != nil {
		return err
	}
	return p.publish(ctx, snapshot)
}

// Reader owns a single key; callers must bound key count and total request concurrency.
type Reader struct {
	mu                    sync.Mutex
	current               Snapshot
	localUntil            time.Time
	inflight              chan struct{}
	load                  func(context.Context) (Snapshot, error)
	localTTL, loadTimeout time.Duration
	now                   func() time.Time
}

func NewReader(load func(context.Context) (Snapshot, error), localTTL, loadTimeout time.Duration) (*Reader, error) {
	if load == nil || localTTL <= 0 || loadTimeout <= 0 {
		return nil, errors.New("invalid reader configuration")
	}
	return &Reader{load: load, localTTL: localTTL, loadTimeout: loadTimeout, now: time.Now}, nil
}

func (r *Reader) Get(ctx context.Context) (Snapshot, error) {
	for {
		if err := ctx.Err(); err != nil {
			return Snapshot{}, err
		}
		r.mu.Lock()
		if now := r.now(); now.Before(r.localUntil) && now.Before(r.current.ExpiresAt) {
			result := clone(r.current)
			r.mu.Unlock()
			return result, nil
		}
		if r.inflight == nil {
			r.inflight = make(chan struct{})
			go r.refresh(r.inflight)
		}
		done := r.inflight
		r.mu.Unlock()
		select {
		case <-ctx.Done():
			return Snapshot{}, ctx.Err()
		case <-done:
			// A failed load is not retried in this call. All waiters observe the same flight.
			r.mu.Lock()
			result := clone(r.current)
			valid := r.now().Before(r.localUntil) && r.now().Before(result.ExpiresAt)
			r.mu.Unlock()
			if !valid {
				return Snapshot{}, ErrUnavailable
			}
			return result, nil
		}
	}
}

func (r *Reader) refresh(done chan struct{}) {
	// A canceled waiter must not cancel the shared load; its lifetime is independently bounded.
	ctx, cancel := context.WithTimeout(context.Background(), r.loadTimeout)
	defer cancel()
	snapshot, err := r.load(ctx)
	now := r.now()
	if err == nil {
		err = snapshot.Validate(now)
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if err == nil {
		r.current = clone(snapshot)
		r.localUntil = now.Add(r.localTTL)
		if snapshot.ExpiresAt.Before(r.localUntil) {
			r.localUntil = snapshot.ExpiresAt
		}
	}
	close(done)
	r.inflight = nil
}
