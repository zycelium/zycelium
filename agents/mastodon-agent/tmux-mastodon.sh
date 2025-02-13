#!/bin/sh

SESSION="mastodon-agent"

# Check if the session exists, create if it doesn't
if ! tmux has-session -t $SESSION 2>/dev/null; then
    # Create a new session
    tmux new-session -d -s $SESSION
    # Run the mastodon agent
    tmux send-keys -t $SESSION "./mastodon-agent --debug" C-m
fi

# Attach to the session
tmux attach -t $SESSION
