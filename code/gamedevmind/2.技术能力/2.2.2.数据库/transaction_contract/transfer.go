// Package contract demonstrates one-database atomicity and durable request identity.
// It is not a payment, authentication or distributed transaction implementation.
package contract

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"math"
	"regexp"

	"github.com/go-sql-driver/mysql"
)

var (
	ErrInvalid      = errors.New("invalid transfer")
	ErrConflict     = errors.New("request ID reused with different parameters")
	ErrInsufficient = errors.New("insufficient balance")
	ErrOverflow     = errors.New("recipient balance overflow")
)

type Request struct {
	ID               string
	From, To, Amount int64
}

func (r Request) Validate() error {
	if len(r.ID) == 0 || len(r.ID) > 64 || r.From <= 0 || r.To <= 0 || r.From == r.To || r.Amount <= 0 {
		return ErrInvalid
	}
	return nil
}

type Store struct {
	db                   *sql.DB
	accounts, operations string
}

func NewStore(db *sql.DB, prefix string) (*Store, error) {
	// Identifiers cannot be passed as SQL values; allow only a controlled fixture/application prefix.
	if db == nil || !regexp.MustCompile(`^db_[a-z0-9]{1,30}$`).MatchString(prefix) {
		return nil, ErrInvalid
	}
	return &Store{db: db, accounts: prefix + "_accounts", operations: prefix + "_operations"}, nil
}

// Transfer returns replay=true only when this exact request was committed previously.
// Callers retry/query with the SAME ID if commit acknowledgement is lost.
func (s *Store) Transfer(ctx context.Context, request Request) (replay bool, err error) {
	if err = request.Validate(); err != nil {
		return false, err
	}
	if err = ctx.Err(); err != nil {
		return false, err
	}
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelReadCommitted})
	if err != nil {
		return false, err
	}
	defer tx.Rollback() // Releases any uncommitted reservation or account update on all failures.
	_, err = tx.ExecContext(ctx, fmt.Sprintf("INSERT INTO `%s` (request_id,from_id,to_id,amount) VALUES (?,?,?,?)", s.operations),
		request.ID, request.From, request.To, request.Amount)
	if err != nil {
		var databaseError *mysql.MySQLError
		if !errors.As(err, &databaseError) || databaseError.Number != 1062 {
			return false, err
		}
		var original Request
		err = tx.QueryRowContext(ctx, fmt.Sprintf("SELECT from_id,to_id,amount FROM `%s` WHERE request_id=?", s.operations),
			request.ID).Scan(&original.From, &original.To, &original.Amount)
		if err != nil {
			return false, err
		}
		if original.From != request.From || original.To != request.To || original.Amount != request.Amount {
			return false, ErrConflict
		}
		// No new changes on this path; rollback releases the duplicate-key statement's locks.
		return true, nil
	}
	// Acquire exact primary-key locks in one global order. Do not rely on ORDER BY to define lock acquisition.
	low, high := request.From, request.To
	if low > high {
		low, high = high, low
	}
	balances := make(map[int64]int64, 2)
	for _, id := range []int64{low, high} {
		var balance int64
		err = tx.QueryRowContext(ctx, fmt.Sprintf("SELECT balance FROM `%s` WHERE id=? FOR UPDATE", s.accounts), id).Scan(&balance)
		if err != nil {
			return false, err
		}
		balances[id] = balance
	}
	if balances[request.From] < request.Amount {
		return false, ErrInsufficient
	}
	if balances[request.To] > math.MaxInt64-request.Amount {
		return false, ErrOverflow
	}
	for _, change := range []struct{ id, delta int64 }{{request.From, -request.Amount}, {request.To, request.Amount}} {
		result, writeErr := tx.ExecContext(ctx, fmt.Sprintf("UPDATE `%s` SET balance=balance+? WHERE id=?", s.accounts), change.delta, change.id)
		if writeErr != nil {
			return false, writeErr
		}
		count, countErr := result.RowsAffected()
		if countErr != nil {
			return false, countErr
		}
		if count != 1 {
			return false, errors.New("account update did not affect exactly one row")
		}
	}
	if err = tx.Commit(); err != nil {
		return false, fmt.Errorf("commit outcome may be unknown; retain request ID: %w", err)
	}
	return false, nil
}
