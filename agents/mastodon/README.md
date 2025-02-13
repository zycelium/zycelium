Get service info

nats req '$SRV.INFO.mastodon' ''

Get stats

nats req '$SRV.STATS.mastodon' ''

Subscribe to timeline

nats sub 'mastodon.stream.*.*.timeline.home'
