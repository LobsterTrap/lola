package cmd

import "testing"

func TestResolveVersion(t *testing.T) {
	tt := []struct {
		name          string
		version       string
		moduleVersion string
		vcsRevision   string
		want          string
	}{
		{"release build",     "v1.2.0", "(devel)", "a3f9b12abc", "v1.2.0"},
		{"go install",        "",       "v1.2.0",  "",           "v1.2.0"},
		{"dev with commit",   "",       "(devel)", "a3f9b12abc", "0.0.0-dev+a3f9b12"},
		{"dev short hash",    "",       "(devel)", "abc",        "0.0.0-dev+abc"},
		{"dev exact 7 hash",  "",       "(devel)", "a3f9b12",    "0.0.0-dev+a3f9b12"},
		{"dev no vcs",        "",       "(devel)", "",           "0.0.0-dev"},
		{"no context at all", "",       "",        "",           "0.0.0-dev"},
	}
	for _, tc := range tt {
		t.Run(tc.name, func(t *testing.T) {
			if got := resolveVersion(tc.version, tc.moduleVersion, tc.vcsRevision); got != tc.want {
				t.Errorf("got %q, want %q", got, tc.want)
			}
		})
	}
}
