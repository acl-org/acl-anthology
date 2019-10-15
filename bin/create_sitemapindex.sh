#! /bin/bash
#
# Copyright 2019 Arne Köhn <arne@chark.eu
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

# Creates a sitemapindex.xml from a list of sitemap files
# Usage: create_sitemapindex.sh [sitemap files] > sitemapindex.xml

echo '<?xml version="1.0" encoding="UTF-8"?>'
echo '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'

for f in "$@"; do
	echo '  <sitemap>'
    echo '    <loc>https://www.aclweb.org/anthology/'$f'</loc>'
	echo '  </sitemap>'
done
echo '</sitemapindex>'
