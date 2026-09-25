package http

import (
	"log/slog"
	stdhttp "net/http"
	"time"

	"request-ranging/executor-balancer/internal/transport/http/handlers"
)

type Handlers struct {
	System *handlers.SystemHandler
}

type Server struct {
	logger   *slog.Logger
	handlers Handlers
}

func NewServer(logger *slog.Logger, systemHandler *handlers.SystemHandler) *Server {
	return &Server{
		logger: logger,
		handlers: Handlers{
			System: systemHandler,
		},
	}
}

func (s *Server) Handler() stdhttp.Handler {
	mux := stdhttp.NewServeMux()
	handlers.StartSystemHandler(mux, s.handlers.System)
	return s.requestLogger(mux)
}

func (s *Server) requestLogger(next stdhttp.Handler) stdhttp.Handler {
	return stdhttp.HandlerFunc(func(response stdhttp.ResponseWriter, request *stdhttp.Request) {
		startedAt := time.Now()
		next.ServeHTTP(response, request)
		s.logger.Info("http request",
			"method", request.Method,
			"path", request.URL.Path,
			"duration_ms", time.Since(startedAt).Milliseconds(),
		)
	})
}
