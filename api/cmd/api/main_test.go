package main

import (
	"reflect"
	"testing"
)

func TestRateFromEnv(t *testing.T) {
	for _, tc := range []struct {
		in      string
		want    int
		wantErr bool
	}{
		{"", 120, false},
		{"30", 30, false},
		{"0", 0, true},
		{"-5", 0, true},
		{"abc", 0, true},
	} {
		got, err := rateFromEnv(tc.in)
		if (err != nil) != tc.wantErr || got != tc.want {
			t.Errorf("rateFromEnv(%q) = %d, %v; want %d, err=%v", tc.in, got, err, tc.want, tc.wantErr)
		}
	}
}

func TestOriginsFromEnv(t *testing.T) {
	for _, tc := range []struct {
		in   string
		want []string
	}{
		{"", []string{"http://localhost:8765"}},
		{" , ", []string{"http://localhost:8765"}},
		{"https://a.example, https://b.example,,", []string{"https://a.example", "https://b.example"}},
	} {
		if got := originsFromEnv(tc.in); !reflect.DeepEqual(got, tc.want) {
			t.Errorf("originsFromEnv(%q) = %v; want %v", tc.in, got, tc.want)
		}
	}
}
