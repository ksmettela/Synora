package geoip

import (
	"context"
	"fmt"
	"net"
	"sync"
	"time"

	"github.com/oschwald/geoip2-golang"
	"go.uber.org/zap"
)

// Filter implements IP-based geoIP filtering
type Filter struct {
	reader       *geoip2.Reader
	cache        sync.Map // map[string]cacheEntry
	logger       *zap.Logger
	mutex        sync.RWMutex
	datacenters  map[string]bool
}

type cacheEntry struct {
	allowed    bool
	expiration time.Time
}

// NewFilter creates a new geoIP filter
func NewFilter(dbPath string, logger *zap.Logger) (*Filter, error) {
	reader, err := geoip2.Open(dbPath)
	if err != nil {
		logger.Warn("failed to open GeoIP database", zap.String("path", dbPath), zap.Error(err))
		// Don't fail startup if GeoIP is missing
		return &Filter{
			logger:      logger,
			cache:       sync.Map{},
			datacenters: initDatacenters(),
		}, nil
	}

	return &Filter{
		reader:       reader,
		logger:       logger,
		datacenters: initDatacenters(),
	}, nil
}

// IsAllowed checks if an IP address is allowed
// Returns false if IP is from a known datacenter or Tor exit node
func (f *Filter) IsAllowed(ctx context.Context, ipStr string) bool {
	// Check cache first
	if cached, ok := f.cache.Load(ipStr); ok {
		entry := cached.(cacheEntry)
		if time.Now().Before(entry.expiration) {
			return entry.allowed
		}
		f.cache.Delete(ipStr)
	}

	allowed := f.checkIP(ipStr)

	// Cache result for 1 hour
	f.cache.Store(ipStr, cacheEntry{
		allowed:    allowed,
		expiration: time.Now().Add(time.Hour),
	})

	return allowed
}

func (f *Filter) checkIP(ipStr string) bool {
	ip := net.ParseIP(ipStr)
	if ip == nil {
		f.logger.Warn("invalid IP address", zap.String("ip", ipStr))
		return true // Allow on parse error
	}

	// Check if IP is from known datacenter ASN
	if f.reader != nil {
		asn, err := f.reader.ASN(context.Background(), ip)
		if err != nil {
			f.logger.Debug("failed to lookup ASN", zap.String("ip", ipStr), zap.Error(err))
		} else {
			// Check known datacenter ASNs
			if f.datacenters[fmt.Sprintf("%d", asn.AutonomousSystemNumber)] {
				f.logger.Debug("IP rejected: datacenter ASN", zap.String("ip", ipStr), zap.Uint("asn", asn.AutonomousSystemNumber))
				return false
			}
		}
	}

	// Check private IP ranges (allow them)
	if ip.IsPrivate() || ip.IsLoopback() {
		return true
	}

	return true
}

// Close closes the GeoIP reader
func (f *Filter) Close() error {
	if f.reader != nil {
		return f.reader.Close()
	}
	return nil
}

// initDatacenters returns a map of known datacenter ASNs
func initDatacenters() map[string]bool {
	return map[string]bool{
		// AWS
		"16509": true,
		"14061": true,
		// Google Cloud
		"15169": true,
		// Microsoft Azure
		"8075": true,
		"8068": true,
		// Linode/Akamai
		"63949": true,
		// DigitalOcean
		"14061": true,
		// Vultr
		"20473": true,
		// Hetzner
		"24940": true,
		// OVH
		"16276": true,
		// Tor exit nodes (Tor Project ASN)
		"6697": true,
	}
}
