package contract

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"math"
	"os"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestRequestValidation(t *testing.T) {
	for _, request := range []Request{{"", 1, 2, 1}, {"x", 1, 1, 1}, {"x", 1, 2, -1}, {"x", 0, 2, 1}} {
		if request.Validate() == nil {
			t.Fatal("unsafe request accepted", request)
		}
	}
}

func TestMySQLTransactionContracts(t *testing.T) {
	dsn := os.Getenv("DATABASE_CONTRACT_MYSQL_DSN")
	if dsn == "" {
		if os.Getenv("REQUIRE_DATABASE_INTEGRATION") == "1" {
			t.Fatal("real MySQL configuration required")
		}
		t.Skip("set DATABASE_CONTRACT_MYSQL_DSN for real InnoDB transaction tests")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	db.SetMaxOpenConns(8)
	db.SetMaxIdleConns(8)
	var database string
	if err = db.QueryRowContext(ctx, "SELECT DATABASE()").Scan(&database); err != nil {
		t.Fatal(err)
	}
	if database != "database_regression" {
		t.Fatal("use only a disposable database_regression database")
	}
	store, err := NewStore(db, fmt.Sprintf("db_%x", time.Now().UnixNano()))
	if err != nil {
		t.Fatal(err)
	}
	// New unique tables only. No DROP, DELETE, TRUNCATE or production schema migration.
	_, err = db.ExecContext(ctx, fmt.Sprintf("CREATE TABLE `%s` (id BIGINT PRIMARY KEY, balance BIGINT NOT NULL CHECK(balance>=0)) ENGINE=InnoDB", store.accounts))
	if err != nil {
		t.Fatal(err)
	}
	_, err = db.ExecContext(ctx, fmt.Sprintf("CREATE TABLE `%s` (request_id VARBINARY(64) PRIMARY KEY, from_id BIGINT NOT NULL, to_id BIGINT NOT NULL, amount BIGINT NOT NULL CHECK(amount>0)) ENGINE=InnoDB", store.operations))
	if err != nil {
		t.Fatal(err)
	}
	seed := func(t *testing.T, id, balance int64) {
		t.Helper()
		if _, err := db.ExecContext(ctx, fmt.Sprintf("INSERT INTO `%s` (id,balance) VALUES (?,?)", store.accounts), id, balance); err != nil {
			t.Fatal(err)
		}
	}
	balance := func(t *testing.T, id int64) int64 {
		t.Helper()
		var result int64
		if err := db.QueryRowContext(ctx, fmt.Sprintf("SELECT balance FROM `%s` WHERE id=?", store.accounts), id).Scan(&result); err != nil {
			t.Fatal(err)
		}
		return result
	}
	operationCount := func(t *testing.T, id string) int {
		t.Helper()
		var count int
		if err := db.QueryRowContext(ctx, fmt.Sprintf("SELECT COUNT(*) FROM `%s` WHERE request_id=?", store.operations), id).Scan(&count); err != nil {
			t.Fatal(err)
		}
		return count
	}
	t.Run("atomic_replay_conflict_and_rollback", func(t *testing.T) {
		seed(t, 1, 100)
		seed(t, 2, 100)
		seed(t, 3, math.MaxInt64)
		req := Request{"one-operation", 1, 2, 30}
		if replay, err := store.Transfer(ctx, req); err != nil || replay {
			t.Fatal(replay, err)
		}
		if replay, err := store.Transfer(ctx, req); err != nil || !replay {
			t.Fatal("committed replay", replay, err)
		}
		if balance(t, 1) != 70 || balance(t, 2) != 130 || operationCount(t, req.ID) != 1 {
			t.Fatal("replay changed balances")
		}
		if _, err := store.Transfer(ctx, Request{req.ID, 1, 2, 31}); !errors.Is(err, ErrConflict) {
			t.Fatal("conflicting ID accepted", err)
		}
		if _, err := store.Transfer(ctx, Request{"too-much", 1, 2, 1000}); !errors.Is(err, ErrInsufficient) {
			t.Fatal(err)
		}
		if _, err := store.Transfer(ctx, Request{"overflow", 1, 3, 1}); !errors.Is(err, ErrOverflow) {
			t.Fatal(err)
		}
		if _, err := store.Transfer(ctx, Request{"missing", 1, 999, 1}); !errors.Is(err, sql.ErrNoRows) {
			t.Fatal(err)
		}
		for _, id := range []string{"too-much", "overflow", "missing"} {
			if operationCount(t, id) != 0 {
				t.Fatal("failed transaction retained request reservation", id)
			}
		}
		if balance(t, 1) != 70 || balance(t, 2) != 130 || balance(t, 3) != math.MaxInt64 {
			t.Fatal("failed transfer changed balances")
		}
	})
	t.Run("concurrent_same_id_and_distinct_requests", func(t *testing.T) {
		seed(t, 5, 100)
		seed(t, 6, 100)
		var wg sync.WaitGroup
		var applied atomic.Int64
		for i := 0; i < 16; i++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				replay, err := store.Transfer(ctx, Request{"concurrent-retry", 5, 6, 1})
				if err != nil {
					t.Error(err)
					return
				}
				if !replay {
					applied.Add(1)
				}
			}()
		}
		wg.Wait()
		if applied.Load() != 1 || balance(t, 5) != 99 || balance(t, 6) != 101 {
			t.Fatal("duplicate effect", applied.Load())
		}
		for i := 0; i < 16; i++ {
			wg.Add(1)
			go func(i int) {
				defer wg.Done()
				if _, err := store.Transfer(ctx, Request{fmt.Sprintf("unique-%d", i), 5, 6, 1}); err != nil {
					t.Error(err)
				}
			}(i)
		}
		wg.Wait()
		if balance(t, 5) != 83 || balance(t, 6) != 117 {
			t.Fatal("lost update or wrong total")
		}
	})
	t.Run("RC_and_RR_read_views", func(t *testing.T) {
		for index, isolation := range []sql.IsolationLevel{sql.LevelReadCommitted, sql.LevelRepeatableRead} {
			left, right := int64(20+index*2), int64(21+index*2)
			seed(t, left, 100)
			seed(t, right, 100)
			tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: isolation, ReadOnly: true})
			if err != nil {
				t.Fatal(err)
			}
			func() {
				defer tx.Rollback()
				var before, after, total int64
				if err := tx.QueryRowContext(ctx, fmt.Sprintf("SELECT balance FROM `%s` WHERE id=?", store.accounts), left).Scan(&before); err != nil {
					t.Fatal(err)
				}
				if _, err := store.Transfer(ctx, Request{fmt.Sprintf("view-%d", index), left, right, 30}); err != nil {
					t.Fatal(err)
				}
				if err := tx.QueryRowContext(ctx, fmt.Sprintf("SELECT balance FROM `%s` WHERE id=?", store.accounts), right).Scan(&after); err != nil {
					t.Fatal(err)
				}
				expected := int64(200)
				if isolation == sql.LevelReadCommitted {
					expected = 230
				}
				if before+after != expected {
					t.Fatal("unexpected consistent-read boundary", isolation, before, after)
				}
				if err := tx.QueryRowContext(ctx, fmt.Sprintf("SELECT SUM(balance) FROM `%s` WHERE id IN (?,?)", store.accounts), left, right).Scan(&total); err != nil {
					t.Fatal(err)
				}
				if total != 200 {
					t.Fatal("single-statement invariant broken", total)
				}
			}()
		}
	})
	t.Run("canceled_request_has_no_reservation", func(t *testing.T) {
		canceled, stop := context.WithCancel(ctx)
		stop()
		if _, err := store.Transfer(canceled, Request{"canceled", 1, 2, 1}); !errors.Is(err, context.Canceled) {
			t.Fatal(err)
		}
		if operationCount(t, "canceled") != 0 {
			t.Fatal("canceled request committed")
		}
	})
}
