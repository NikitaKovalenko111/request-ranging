package system

import stdhttp "net/http"

func StartSystemHandler(mux *stdhttp.ServeMux, handler *Handler) {
	mux.HandleFunc("GET /health", handler.Health)
	mux.HandleFunc("GET /ready", handler.Ready)
}
