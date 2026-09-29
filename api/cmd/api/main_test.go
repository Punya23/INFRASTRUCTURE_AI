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
		in      string
		want    []string
		wantErr bool
	}{
		{"", []string{"http://localhost:8765"}, false},
		{" , ", []string{"http://localhost:8765"}, false},
		{"https://a.example, https://b.example,,", []string{"https://a.example", "https://b.example"}, false},
		{"http://localhost:8765", []string{"http://localhost:8765"}, false},
		{"*", nil, true},
		{"https://a.example/", nil, true},
		{"a.example", nil, true},
		{"ftp://a.example", nil, true},
		{"https://a.example/x", nil, true},
		{"https://user@a.example", nil, true},
		{"https://ok.example,https://bad.example/", nil, true},
	} {
		got, err := originsFromEnv(tc.in)
		if (err != nil) != tc.wantErr || !reflect.DeepEqual(got, tc.want) {
			t.Errorf("originsFromEnv(%q) = %v, %v; want %v, err=%v", tc.in, got, err, tc.want, tc.wantErr)
		}
	}
}
