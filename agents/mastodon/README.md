Get service info

nats req '$SRV.INFO.mastodon' ''

Get stats

nats req '$SRV.STATS.mastodon' ''

Subscribe to timeline

nats sub 'mastodon.stream.*.*.timeline.home'

View timeline stream for all instances and users:

```
nats sub 'mastodon.stream.>'
```

View timeline for specific instance and user:

```
nats sub 'mastodon.stream.mastodon_social.username.timeline.home'
```

Sending post
-----------

To post a new status, send a request with the text content:

```
nats req 'mastodon.post.now' 'Hello from NATS!'
```
