package auth

import (
	"context"
	"net/http"
)

type User struct {
	ID string
}

type ctxKey struct{}

var sessions = map[string]User{}

// Require rejects requests without a session user; it does not check what the user may access.
func Require(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user, ok := sessionUser(r)
		if !ok {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), ctxKey{}, user)))
	})
}

// UserFrom returns the user that Require stored in the context.
func UserFrom(ctx context.Context) User {
	user, _ := ctx.Value(ctxKey{}).(User)
	return user
}

func sessionUser(r *http.Request) (User, bool) {
	cookie, err := r.Cookie("session")
	if err != nil {
		return User{}, false
	}
	user, ok := sessions[cookie.Value]
	return user, ok
}
