# -*- coding: utf-8 -*-
#
# Copyright 2019-2020 Marcel Bollmann <marcel@bollmann.me>
# Copyright 2022 Matt Post <post@cs.jhu.edu>
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


from anthology.utils import parse_element
from anthology.formatter import MarkupFormatter
from anthology.data import EVENT_LOCATION_TEMPLATE


class EventIndex:
    """
    Keeps track of all events in the anthology and their relation to venues and volumes.
    Events are both explicitly represented in a collections <event> block, and are also
    implicit: every volume has one or more <venue> tags, as well as a year, and this information
    is used to add each volume to its event. For example, if a volume in year YYYY is
    has <venue>X</venue>, it will appear in the event named X-YYYY.

    This still leaves some events semi-implicit, since they are not listed explicitly in
    the <event> block. We may wish to change this in the future.
    """

    def __init__(self, venue_index):
        """
        :param venue_index: A VenueIndex object
        """
        self.events = {}
        self.venue_index = venue_index
        self.formatter = MarkupFormatter()

    def _create_event(self, event_id):
        """
        Creates an event, if it doesn't already exist. Initializes the event title
        to a default value that can later be overridden.
        """
        if event_id not in self.events:
            venue, year = event_id.split("-")
            venue_name = self.venue_index.get_venue(venue)["name"]
            self.events[event_id] = {
                "venue": venue,
                "year": year,
                "title": f"{venue_name} ({year})",
                "links": [],
                "volumes": [],
            }

    def register_event(self, event_xml):
        """
        Creates a new event from the <event> block in the XML.
        """
        event_id = event_xml.attrib["id"]
        self._create_event(event_id)

        # parse the top level of the block
        event_data = parse_element(
            event_xml,
            list_elements=["url", "volume-id"],
            dont_parse_elements=["meta", "links", "colocated"],
        )

        # copy over on top of default values
        for key, value in event_data.items():
            if key == "xml_meta":
                # parse the children of "meta", raising them to the top level
                # We also apply the formatter to the title, even though it shouldn't
                # contain sub-formatting like that found in tables
                for childkey, childvalue in parse_element(value).items():
                    if childkey == "xml_title":
                        # This item preserves the XML, so we need to interpret it
                        self.events[event_id]["title"] = self.formatter(
                            childvalue, "text"
                        )
                    else:
                        self.events[event_id][childkey] = childvalue

            elif key == "xml_links":
                # Copy links as a list of dicts under "links". This is then iterated over
                # in the hugo template (hugo/layouts/events/single.html
                for name, url in parse_element(value, list_elements=["url"]).items():
                    # Rewrite the handbook URL if it's a relative path (which it should be)
                    if (
                        name == "handbook"
                        and not url.startswith("http")
                        and not url.startswith("/")
                    ):
                        url = EVENT_LOCATION_TEMPLATE.format(url)

                    self.events[event_id]["links"].append({name.capitalize(): url})

            elif key == "xml_colocated":
                # Turn the colocated volumes into a list of volume IDs
                for volume_id in parse_element(value, list_elements=["volume-id"]).get(
                    "volume-id", []
                ):
                    self.register_volume(volume_id, event_id)

            else:
                # all other keys
                self.events[event_id][key] = value

        # print(event_id, self.events[event_id])

    def register_volume(self, volume: str, event_id: str):
        """
        Adds a volume to an event. These are the volumes that will appear on the
        event page. It should include volumes naturally associated with the event
        (by virtue of belonging to the event's venue) as well as colocated volumes.

        :param volume: The full volume ID (e.g., P19-1, 2022.acl-long)
        :param event: The event (e.g., acl-2019, acl-2022)
        """
        self._create_event(event_id)

        if volume not in self.events[event_id]["volumes"]:
            self.events[event_id]["volumes"].append(volume)

    def items(self):
        """Iterate over the events."""
        return self.events.items()
