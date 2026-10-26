package main

import (
	"database/sql"
	"log"
	"net/http"

	_ "github.com/lib/pq"

	"example.com/billing/internal/auth"
	"example.com/billing/internal/invoices"
)

func main() {
	db, err := sql.Open("postgres", "postgres://localhost/billing")
	if err != nil {
		log.Fatal(err)
	}
	h := &invoices.Handler{Store: &invoices.Store{DB: db}}
	mux := http.NewServeMux()
	mux.Handle("/invoices/", auth.Require(http.HandlerFunc(h.Download)))
	log.Fatal(http.ListenAndServe(":8080", mux))
}
