package http

import (
	"log/slog"
	stdhttp "net/http"
	"time"

	apihandler "request-ranging/executor-balancer/internal/transport/http/handlers/api"
	"request-ranging/executor-balancer/internal/transport/http/handlers/system"
)

type Handlers struct {
	System *system.Handler
	API    *apihandler.Handler
}

type Server struct {
	logger   *slog.Logger
	handlers Handlers
}

func NewServer(logger *slog.Logger, systemHandler *system.Handler, apiHandlers ...*apihandler.Handler) *Server {
	var apiHandler *apihandler.Handler
	if len(apiHandlers) > 0 {
		apiHandler = apiHandlers[0]
	}
	return &Server{
		logger: logger,
		handlers: Handlers{
			System: systemHandler,
			API:    apiHandler,
		},
	}
}

func (s *Server) Handler() stdhttp.Handler {
	mux := stdhttp.NewServeMux()
	system.StartSystemHandler(mux, s.handlers.System)
	if s.handlers.API != nil {
		apihandler.Register(mux, s.handlers.API)
	}
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
