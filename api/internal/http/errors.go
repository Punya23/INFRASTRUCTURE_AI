package httpapi

import (
	"encoding/json"
	"io"
	"net/http"
)

// errorBody is the JSON of an error response, {"error":{"code","message"}}: the only shape an error takes.
// Marshalling two strings cannot fail.
func errorBody(code, message string) string {
	b, _ := json.Marshal(map[string]map[string]string{"error": {"code": code, "message": message}})
	return string(b)
}

// errorHeaders marks a response as a JSON error that no cache may keep.
func errorHeaders(h http.Header) {
	h.Set("Content-Type", "application/json")
	h.Set("Cache-Control", "no-store")
}

// writeError answers with the error shape. The message is written for the client: never pass it an internal
// error's text.
func writeError(w http.ResponseWriter, status int, code, message string) {
	errorHeaders(w.Header())
	w.WriteHeader(status)
	_, _ = io.WriteString(w, errorBody(code, message))
}
