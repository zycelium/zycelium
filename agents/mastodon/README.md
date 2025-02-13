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
nats sub 'mastodon.stream.mastodon_social.username.timeline.home'
```

## Post on Mastodon

To post a new status, send a request with the text content:

```bash
nats req 'mastodon.post.now' 'Hello from NATS!'
```
