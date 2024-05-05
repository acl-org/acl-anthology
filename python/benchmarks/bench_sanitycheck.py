# Copyright 2023-2024 Marcel Bollmann <marcel@bollmann.me>
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

REPEAT = 1_000

# This file exists so that there's no doubt which columns are A and B in the
# richbench output, and how the description string should be interpreted.


def count_to_100():
    for _ in range(REPEAT):
        j = 0
        for i in range(100):
            j += 1


def count_to_1000():
    for _ in range(REPEAT):
        j = 0
        for i in range(1_000):
            j += 1


__benchmarks__ = [
    (
        count_to_1000,
        count_to_100,
        "Count to 1000 vs. count to 100",
    ),
]
