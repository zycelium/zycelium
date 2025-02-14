# Zycelium Hello Agent

A simple demonstration agent that responds to hello requests with customizable greetings.

## Service Information

Get service info:

```bash
nats req '$SRV.INFO.hello' ''
```

## Basic Usage

Send a hello request with an optional name:

```bash
nats req 'hello' 'Alice'    # Returns: Hello, Alice!
nats req 'hello' ''         # Returns: Hello, World!
```

## Configuration

The agent can be configured using a TOML configuration file or through the NATS Key-Value store:

### Initial Configuration

```toml
debug = true        # Enable debug logging
capitalize = false  # Control capitalization of responses
nats_urls = ["nats://localhost:4222"]
```

### Dynamic Configuration

The `capitalize` setting can be changed at runtime through the NATS KV store:

```bash
# Set capitalize to true to get uppercase responses
nats kv put hello_config capitalize true

# Set capitalize to false for normal responses
nats kv put hello_config capitalize false
```

When capitalize is enabled:

```bash
nats req 'hello' 'Alice'    # Returns: HELLO, ALICE!
```
