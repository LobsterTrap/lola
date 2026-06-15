// Package modules implements Lola's module management domain logic.
package modules

import "errors"

// ErrNotImplemented is returned by stub functions that have not yet been implemented.
// It serves as the template for domain-specific errors (e.g. ErrModuleNotFound) that
// will be added to this file as each function is implemented.
var ErrNotImplemented = errors.New("not yet implemented")
