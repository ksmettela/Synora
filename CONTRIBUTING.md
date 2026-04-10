# Contributing to Synora

## Development Setup

1. Clone the repository
2. Copy `.env.example` to `.env`
3. Run `docker-compose up -d`
4. Run `./docker-compose.init.sh`

## Code Organization

- `sdk/` - C++17 SDK for client-side fingerprinting
- `services/` - Microservices (Go, Python, Rust)
- `data-pipeline/` - Batch and stream processing
- `frontend/` - React dashboard
- `infra/` - Terraform and Kubernetes manifests

## Making Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `make test`
4. Format code: `make format`
5. Commit with descriptive message
6. Push and create a Pull Request

## Testing

```bash
make test              # Run all tests
make test-coverage     # With coverage reports
```

## Code Style

- Go: `gofmt`, `golangci-lint`
- Python: `black`, `isort`, `pylint`
- Rust: `rustfmt`, `clippy`
- TypeScript: ESLint, Prettier

## Documentation

Update relevant documentation when making changes:
- API changes → `docs/API_REFERENCE.md`
- Architecture changes → `docs/ARCHITECTURE.md`
- Deployment changes → `docs/DEPLOYMENT.md`

## Reporting Issues

Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, versions, etc.)
