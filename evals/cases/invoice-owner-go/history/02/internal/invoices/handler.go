package invoices

import (
	"net/http"
	"strings"

	"example.com/billing/internal/auth"
)

type Handler struct {
	Store *Store
}

// Download serves GET /invoices/{id} as a PDF.
func (h *Handler) Download(w http.ResponseWriter, r *http.Request) {
	user := auth.UserFrom(r.Context())
	id := strings.TrimPrefix(r.URL.Path, "/invoices/")
	inv, err := h.Store.Find(r.Context(), id)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if inv.OwnerID != user.ID {
		http.Error(w, "forbidden", http.StatusForbidden)
		return
	}
	w.Header().Set("Content-Type", "application/pdf")
	w.Write(inv.PDF)
}
