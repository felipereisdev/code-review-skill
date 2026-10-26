package invoices

import (
	"net/http"
	"strings"
)

type Handler struct {
	Store *Store
}

// Download serves GET /invoices/{id} as a PDF.
func (h *Handler) Download(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/invoices/")
	inv, err := h.Store.Find(r.Context(), id)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "application/pdf")
	w.Write(inv.PDF)
}
