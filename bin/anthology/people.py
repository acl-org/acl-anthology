# Marcel Bollmann <marcel@bollmann.me>, 2019

from collections import defaultdict


class PersonName:
    first, last, jr = "", "", ""

    def __init__(self, first, last, jr):
        self.first = first.strip()
        self.last = last.strip()
        self.jr = jr.strip()

    def from_element(person_element):
        first, last, jr = "", "", ""
        for element in person_element:
            tag = element.tag
            # These are guaranteed to occur at most once by the schema
            if tag == "first":
                first = element.text or ""
            elif tag == "last":
                last = element.text or ""
            elif tag == "jr":
                jr = element.text or ""
        return PersonName(first, last, jr)

    @property
    def full(self):
        return "{} {}{}".format(self.first, self.last, self.jr).strip()

    @property
    def id_(self):
        return repr(self)

    def as_dict(self):
        return {
            "first": self.first,
            "last": self.last,
            "jr": self.jr,
            "full": self.full,
        }

    def __eq__(self, other):
        return (
            (self.first == other.first)
            and (self.last == other.last)
            and (self.jr == other.jr)
        )

    def __str__(self):
        return self.full

    def __repr__(self):
        if self.jr:
            return "{} || {} || {}".format(self.first, self.last, self.jr)
        elif self.first:
            return "{} || {}".format(self.first, self.last)
        else:
            return self.last

    def __hash__(self):
        return hash(repr(self))


class PersonIndex:
    """Keeps an index of persons and their associated papers."""

    def __init__(self):
        self.names = {}  # maps name strings to PersonName objects
        self.papers = defaultdict(lambda: defaultdict(list))

    def register(self, name: PersonName, paper_id, role):
        """Adds a name to the index, associates it with the given paper ID and role, and returns the name's unique representation."""
        assert isinstance(name, PersonName), "Expected PersonName, got {} ({})".format(
            type(name), repr(name)
        )
        if repr(name) not in self.names:
            self.names[repr(name)] = name
        self.papers[name][role].append(paper_id)
        return repr(name)

    def items(self):
        for name_repr, name in self.names.items():
            yield name_repr, name, self.papers[name]

    def __len__(self):
        return len(self.names)
