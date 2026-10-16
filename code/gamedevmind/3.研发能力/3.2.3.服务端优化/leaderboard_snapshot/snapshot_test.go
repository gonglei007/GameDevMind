package leaderboard

import (
	"context"
	"encoding/json"
	"errors"
	"reflect"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func fixture(now time.Time) Snapshot {
	return Snapshot{Version: "v1", CapturedAt: now, ExpiresAt: now.Add(time.Minute),
		Entries: []Entry{{1, 1<<53 + 1}, {2, 1<<53 + 1}, {3, 100}}}
}

func TestOrderPrecisionAndCursor(t *testing.T) {
	s := fixture(time.Now())
	encoded, err := json.Marshal(s)
	if err != nil {
		t.Fatal(err)
	}
	var decoded Snapshot
	if err = json.Unmarshal(encoded, &decoded); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(s.Entries, decoded.Entries) {
		t.Fatal("integer precision lost")
	}
	if err = decoded.Validate(time.Now()); err != nil {
		t.Fatal(err)
	}
	first, cursor, err := Page(s, nil, 1)
	if err != nil || first[0].UID != 1 || cursor == nil {
		t.Fatal(first, cursor, err)
	}
	second, cursor, err := Page(s, cursor, 1)
	if err != nil || second[0].UID != 2 || cursor == nil {
		t.Fatal("equal-score row skipped", err)
	}
	s.Version = "v2"
	if _, _, err = Page(s, cursor, 1); !errors.Is(err, ErrCursorVersion) {
		t.Fatal("cross-version cursor accepted")
	}
	s.Entries[0], s.Entries[1] = s.Entries[1], s.Entries[0]
	if s.Validate(time.Now()) == nil {
		t.Fatal("invalid tie order accepted")
	}
	if _, _, err = Page(s, nil, 0); err == nil {
		t.Fatal("zero limit accepted")
	}
}

func TestReaderExpiryIsolationAndEmpty(t *testing.T) {
	base := time.Now()
	var elapsed atomic.Int64
	now := func() time.Time { return base.Add(time.Duration(elapsed.Load())) }
	s := fixture(base)
	s.ExpiresAt = base.Add(time.Second)
	var calls atomic.Int64
	r, _ := NewReader(func(context.Context) (Snapshot, error) { calls.Add(1); return s, nil },
		800*time.Millisecond, time.Second)
	r.now = now
	got, err := r.Get(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	got.Entries[0].Power = 0
	got, err = r.Get(context.Background())
	if err != nil || got.Entries[0].Power != s.Entries[0].Power {
		t.Fatal("mutable slice escaped", err)
	}
	elapsed.Store(int64(900 * time.Millisecond))
	if _, err = r.Get(context.Background()); err != nil {
		t.Fatal(err)
	}
	elapsed.Store(int64(1100 * time.Millisecond))
	if _, err = r.Get(context.Background()); !errors.Is(err, ErrUnavailable) {
		t.Fatal("L1 renewed expired source", err)
	}
	if calls.Load() != 3 {
		t.Fatal("unexpected source loads", calls.Load())
	}
	var emptyLoads atomic.Int64
	empty := fixture(time.Now())
	empty.Entries = []Entry{}
	emptyReader, _ := NewReader(func(context.Context) (Snapshot, error) { emptyLoads.Add(1); return empty, nil },
		time.Minute, time.Second)
	for i := 0; i < 3; i++ {
		got, err = emptyReader.Get(context.Background())
		if err != nil || len(got.Entries) != 0 {
			t.Fatal("empty board treated as missing", err)
		}
	}
	if emptyLoads.Load() != 1 {
		t.Fatal("empty board was not cached")
	}
}

func TestConcurrentMissCancellationAndFailure(t *testing.T) {
	started, release := make(chan struct{}), make(chan struct{})
	var calls atomic.Int64
	r, _ := NewReader(func(ctx context.Context) (Snapshot, error) {
		if calls.Add(1) == 1 {
			close(started)
		}
		select {
		case <-release:
			return fixture(time.Now()), nil
		case <-ctx.Done():
			return Snapshot{}, ctx.Err()
		}
	}, time.Minute, time.Second)
	ctx, cancel := context.WithCancel(context.Background())
	firstDone := make(chan error, 1)
	go func() { _, err := r.Get(ctx); firstDone <- err }()
	<-started
	var wg sync.WaitGroup
	for i := 0; i < 32; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := r.Get(context.Background()); err != nil {
				t.Error(err)
			}
		}()
	}
	cancel()
	if err := <-firstDone; !errors.Is(err, context.Canceled) {
		t.Fatal("waiter cancellation ignored", err)
	}
	close(release)
	wg.Wait()
	if calls.Load() != 1 {
		t.Fatal("misses not coalesced", calls.Load())
	}
	failed, _ := NewReader(func(ctx context.Context) (Snapshot, error) {
		<-ctx.Done()
		return Snapshot{}, ctx.Err()
	}, time.Second, 20*time.Millisecond)
	if _, err := failed.Get(context.Background()); !errors.Is(err, ErrUnavailable) {
		t.Fatal("load deadline ignored", err)
	}
}

func TestPublisherRejectsPartialExpiredAndUnordered(t *testing.T) {
	base := time.Now()
	var published atomic.Int64
	sink := func(context.Context, Snapshot) error { published.Add(1); return nil }
	p, _ := NewPublisher(func(context.Context) ([]Entry, error) {
		return []Entry{{1, 100}}, errors.New("rows iteration failed")
	}, sink, time.Second)
	if p.Refresh(context.Background()) == nil || published.Load() != 0 {
		t.Fatal("partial rows published")
	}
	p, _ = NewPublisher(func(context.Context) ([]Entry, error) { return []Entry{{2, 10}, {1, 10}}, nil }, sink, time.Second)
	if p.Refresh(context.Background()) == nil || published.Load() != 0 {
		t.Fatal("unordered rows published")
	}
	var clockCalls int
	p, _ = NewPublisher(func(context.Context) ([]Entry, error) { return []Entry{}, nil }, sink, time.Second)
	p.now = func() time.Time {
		clockCalls++
		if clockCalls == 1 {
			return base
		}
		return base.Add(2 * time.Second)
	}
	if p.Refresh(context.Background()) == nil || published.Load() != 0 {
		t.Fatal("slow source renewed its own freshness")
	}
	p, _ = NewPublisher(func(context.Context) ([]Entry, error) { return []Entry{}, nil }, sink, time.Second)
	if err := p.Refresh(context.Background()); err != nil || published.Load() != 1 {
		t.Fatal("valid empty board rejected", err)
	}
}
