module github.com/zycelium/zycelium/agents/mastodon-agent

go 1.23.3

require (
	github.com/mattn/go-mastodon v0.0.9
	github.com/nats-io/nats.go v1.39.0
	github.com/zycelium/zycelium/agent v0.0.0
)

require (
	github.com/BurntSushi/toml v1.4.0 // indirect
	github.com/gorilla/websocket v1.5.1 // indirect
	github.com/klauspost/compress v1.17.9 // indirect
	github.com/nats-io/nkeys v0.4.9 // indirect
	github.com/nats-io/nuid v1.0.1 // indirect
	github.com/tomnomnom/linkheader v0.0.0-20180905144013-02ca5825eb80 // indirect
	golang.org/x/crypto v0.31.0 // indirect
	golang.org/x/net v0.25.0 // indirect
	golang.org/x/sys v0.28.0 // indirect
)

replace github.com/zycelium/zycelium/agent => ../../agent
