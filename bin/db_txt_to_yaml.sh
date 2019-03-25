#!/bin/bash
#
# Copyright 2019 Marcel Bollmann <marcel@bollmann.me>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This just documents the Ruby one-liner required to convert current db/*.txt files
# to YAML; it can probably be deleted once the transition is complete.

ruby -e 'require "yaml"; String hash = File.read("'"$1"'"); puts eval("{#{hash}}").to_yaml'
