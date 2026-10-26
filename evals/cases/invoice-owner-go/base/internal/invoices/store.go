package invoices

import (
	"context"
	"database/sql"
)

type Invoice struct {
	ID      string
	OwnerID string
	PDF     []byte
}

type Store struct {
	DB *sql.DB
}

// Find loads one invoice by id, whoever owns it.
func (s *Store) Find(ctx context.Context, id string) (*Invoice, error) {
	var inv Invoice
	err := s.DB.QueryRowContext(ctx,
		"SELECT id, owner_id, pdf FROM invoices WHERE id = $1", id,
	).Scan(&inv.ID, &inv.OwnerID, &inv.PDF)
	if err != nil {
		return nil, err
	}
	return &inv, nil
}
