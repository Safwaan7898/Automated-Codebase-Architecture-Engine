package alpha

import (
	"fmt"
	"example.com/gorepo/pkg/beta"
)

type AlphaService struct {
	Beta *beta.BetaService
}

func (a *AlphaService) Run() string {
	if a.Beta == nil {
		return "no-beta"
	}
	return fmt.Sprintf("alpha-%s", a.Beta.Value())
}
