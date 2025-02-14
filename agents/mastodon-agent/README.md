# Zycelium Mastodon Agent

Get service info

```bash
nats req '$SRV.INFO.mastodon' ''
```

Get stats

```bash
nats req '$SRV.STATS.mastodon' ''
```

Subscribe to timeline

```bash
nats sub 'mastodon.stream.*.*.timeline.home'
```

View timeline stream for all instances and users:

```bash
nats sub 'mastodon.stream.>'
```

View timeline for specific instance and user:

```bash
nats sub 'mastodon.stream.{instance_tld}.{username}.timeline.home'
```

## Post on Mastodon

To post a new status, send a request with the text content. The request will be handled by the specific agent that matches both the instance and username:

```bash
nats req 'mastodon.post.{instance_tld}.{username}.now' 'Hello from NATS!'
```

Example:

```bash
nats req 'mastodon.post.mastodon_social.alice.now' 'Hello from Alice!'
nats req 'mastodon.post.fosstodon_org.bob.now' 'Hello from Bob!'
```

Each agent only handles requests for its specific instance and username combination. If no agent exists for the specified combination, the request will timeout.

## Configuration

The agent can be configured through both the configuration file and NATS KV store.

### User Stream Control

The home timeline stream can be enabled/disabled through:

1. Configuration file (`mastodon-agent.conf`):

```toml
user_stream = true  # or false
```

1. NATS KV store:

```bash
# Enable user stream
nats kv put mastodon_config user_stream true

# Disable user stream
nats kv put mastodon_config user_stream false
```

The stream setting can be changed dynamically without restarting the agent.
