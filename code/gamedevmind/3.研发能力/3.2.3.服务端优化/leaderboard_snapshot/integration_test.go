package leaderboard

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"

	_ "github.com/go-sql-driver/mysql"
	"github.com/redis/go-redis/v9"
)

func TestMySQLRedisIntegration(t *testing.T) {
	dsn, addr := os.Getenv("SERVER_OPT_MYSQL_DSN"), os.Getenv("SERVER_OPT_REDIS_ADDR")
	if dsn == "" || addr == "" {
		if os.Getenv("REQUIRE_SERVER_INTEGRATION") == "1" {
			t.Fatal("real MySQL/Redis configuration required")
		}
		t.Skip("set SERVER_OPT_MYSQL_DSN and SERVER_OPT_REDIS_ADDR for real dependency regression")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	db.SetMaxOpenConns(4)
	db.SetMaxIdleConns(4)
	var database string
	if err = db.QueryRowContext(ctx, "SELECT DATABASE()").Scan(&database); err != nil {
		t.Fatal(err)
	}
	if database != "rank_regression" {
		t.Fatal("use only the disposable rank_regression database")
	}
	table := fmt.Sprintf("player_rank_%x", time.Now().UnixNano())
	_, err = db.ExecContext(ctx, "CREATE TABLE `"+table+"` (uid BIGINT PRIMARY KEY, power BIGINT NOT NULL, INDEX idx_order(power DESC, uid ASC))")
	if err != nil {
		t.Fatal(err)
	}
	// No DROP/DELETE/FLUSH: the CI service owns disposable fixtures.
	_, err = db.ExecContext(ctx, "INSERT INTO `"+table+"` (uid,power) VALUES (3,100),(2,9007199254740993),(1,9007199254740993)")
	if err != nil {
		t.Fatal(err)
	}
	loader, err := SQLLoader(db, table, 3)
	if err != nil {
		t.Fatal(err)
	}
	rows, err := loader(ctx)
	if err != nil || !reflect.DeepEqual(rows, []Entry{{1, 9007199254740993}, {2, 9007199254740993}, {3, 100}}) {
		t.Fatal("real SQL total order/int64 mismatch", rows, err)
	}
	client := redis.NewClient(&redis.Options{Addr: addr, PoolSize: 4, MaxRetries: -1,
		ContextTimeoutEnabled: true, DialTimeout: time.Second, ReadTimeout: time.Second, WriteTimeout: time.Second})
	defer client.Close()
	if err = client.Ping(ctx).Err(); err != nil {
		t.Fatal(err)
	}
	store := RedisStore{Client: client, Key: "gamedevmind:test:rank:" + table}
	publisher, _ := NewPublisher(loader, store.Publish, time.Minute)
	if err = publisher.Refresh(ctx); err != nil {
		t.Fatal(err)
	}
	old, err := store.Load(ctx)
	if err != nil || !reflect.DeepEqual(old.Entries, rows) {
		t.Fatal("round trip mismatch", err)
	}
	if ttl := client.PTTL(ctx, store.Key).Val(); ttl <= 0 || ttl > time.Minute {
		t.Fatal("missing or renewed source expiry", ttl)
	}
	failed, _ := NewPublisher(func(context.Context) ([]Entry, error) { return rows[:1], fmt.Errorf("scan failure") }, store.Publish, time.Minute)
	if failed.Refresh(ctx) == nil {
		t.Fatal("expected source failure")
	}
	unchanged, err := store.Load(ctx)
	if err != nil || unchanged.Version != old.Version {
		t.Fatal("failed rebuild replaced good snapshot", err)
	}
	// Concurrent readers must see either complete generation, never DEL/ZADD intermediate states.
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		for i := 0; i < 30; i++ {
			s := fixture(time.Now())
			s.Version = fmt.Sprintf("new-%d", i)
			if err := store.Publish(ctx, s); err != nil {
				t.Error(err)
				return
			}
		}
	}()
	for i := 0; i < 30; i++ {
		s, err := store.Load(ctx)
		if err != nil || len(s.Entries) != 3 || (!strings.HasPrefix(s.Version, "new-") && s.Version != old.Version) {
			t.Error("partial/missing generation", s.Version, err)
		}
	}
	wg.Wait()
	reader, _ := NewReader(store.Load, time.Second, time.Second)
	got, err := reader.Get(ctx)
	if err != nil || len(got.Entries) != 3 {
		t.Fatal("reader integration", err)
	}
	missing := RedisStore{Client: client, Key: store.Key + ":missing"}
	if _, err = missing.Load(ctx); err == nil {
		t.Fatal("missing key accepted as empty board")
	}
}
