#!/bin/bash

SESSION="mastodon-agent"

# Check if the session exists
tmux has-session -t $SESSION 2>/dev/null

if [ $? != 0 ]; then
    # Create a new session
    tmux new-session -d -s $SESSION
    # Run the mastodon agent
    tmux send-keys -t $SESSION "./mastodon-agent --debug" C-m
fi

# Attach to the session
tmux attach -t $SESSION
