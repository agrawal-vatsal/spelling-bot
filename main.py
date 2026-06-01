#!/usr/bin/env python3
"""Thin entrypoint launcher executing the Pipecat runner engine."""

from pipecat.runner.run import main

if __name__ == "__main__":
    # main() dynamically looks into app.bot (or a target runtime file) 
    # to locate and execute the async def bot(runner_args) worker loop.
    main()