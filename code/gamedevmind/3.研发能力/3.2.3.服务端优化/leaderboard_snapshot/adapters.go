package leaderboard

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"time"

	"github.com/redis/go-redis/v9"
)

// SQLLoader executes one consistent SELECT; configure DB deadlines/pool outside this example.
func SQLLoader(db *sql.DB, table string, limit int) (LoadRows, error) {
	if db == nil || !regexp.MustCompile(`^[a-z][a-z0-9_]{0,63}$`).MatchString(table) || limit < 1 || limit > MaxRows {
		return nil, errors.New("invalid SQL loader configuration")
	}
	query := fmt.Sprintf("SELECT uid, power FROM `%s` ORDER BY power DESC, uid ASC LIMIT ?", table)
	return func(ctx context.Context) ([]Entry, error) {
		rows, err := db.QueryContext(ctx, query, limit)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		result := make([]Entry, 0, limit)
		for rows.Next() {
			var entry Entry
			if err := rows.Scan(&entry.UID, &entry.Power); err != nil {
				return nil, err
			}
			result = append(result, entry)
		}
		if err := rows.Err(); err != nil {
			return nil, err
		}
		return result, nil
	}, nil
}

type RedisStore struct {
	Client *redis.Client
	Key    string
}

func (s RedisStore) Publish(ctx context.Context, snapshot Snapshot) error {
	if s.Client == nil || s.Key == "" {
		return ErrUnavailable
	}
	if err := snapshot.Validate(time.Now()); err != nil {
		return err
	}
	payload, err := json.Marshal(snapshot)
	if err != nil {
		return err
	}
	ttl := time.Until(snapshot.ExpiresAt)
	if ttl < time.Millisecond {
		return ErrUnavailable
	} // Never turn a zero TTL into a persistent key.
	// One command atomically replaces the complete bounded snapshot and its expiry.
	// A transport error after sending has an unknown outcome; inspect the version on retry.
	return s.Client.Set(ctx, s.Key, payload, ttl).Err()
}

func (s RedisStore) Load(ctx context.Context) (Snapshot, error) {
	if s.Client == nil || s.Key == "" {
		return Snapshot{}, ErrUnavailable
	}
	payload, err := s.Client.Get(ctx, s.Key).Bytes()
	if err != nil {
		return Snapshot{}, fmt.Errorf("snapshot GET: %w", err)
	}
	if len(payload) > 256*1024 {
		return Snapshot{}, ErrUnavailable
	}
	var snapshot Snapshot
	if err = json.Unmarshal(payload, &snapshot); err != nil {
		return Snapshot{}, err
	}
	if err = snapshot.Validate(time.Now()); err != nil {
		return Snapshot{}, err
	}
	return snapshot, nil
}
