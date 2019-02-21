#!/bin/bash
# Marcel Bollmann <marcel@bollmann.me>, 2019
#
# This just documents the Ruby one-liner required to convert current db/*.txt files
# to YAML; it can probably be deleted once the transition is complete.

ruby -e 'require "yaml"; String hash = File.read("'"$1"'"); puts eval("{#{hash}}").to_yaml'
