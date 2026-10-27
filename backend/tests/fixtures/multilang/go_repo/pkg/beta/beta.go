package beta

import (
	"example.com/gorepo/pkg/alpha"
)

type BetaService struct {
	Alpha *alpha.AlphaService
}

func (b *BetaService) Value() string {
	return "beta-ok"
}
